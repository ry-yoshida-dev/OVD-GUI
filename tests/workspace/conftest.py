import time
from collections.abc import Callable, Iterator, Sequence
from functools import partial
from pathlib import Path
from queue import Empty, SimpleQueue
from typing import ClassVar

import numpy as np
import pytest
from open_vocabulary_detector import DetectionResult, DetectorBackend, ImageSize, OpenVocabularyDetector, Prompt
from PIL import Image

from ovd_gui.detection import DetectorSession, DeviceAvailability
from ovd_gui.preset import PresetCatalog
from ovd_gui.storage import ClassSetStore, ClassThresholdStore, ResultStore, SessionStore
from ovd_gui.vocabulary import ClassDefinition, ClassListStore
from ovd_gui.workspace import ModelSelector, Notice, Workspace, WorkspaceStores, WorkspaceTopic
from ovd_gui.workspace.upload_store import UploadStore


class WidthCountingDetector(OpenVocabularyDetector):
    BACKEND: ClassVar[DetectorBackend] = DetectorBackend.GROUNDING_DINO
    failing_widths: frozenset[int] = frozenset()

    def _detect_mini_batch(self, images: Sequence[Image.Image], prompt: Prompt) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        for image in images:
            if image.width in self.failing_widths:
                raise ValueError("unsupported image")
            count: int = image.width // 32
            results.append(
                DetectionResult.from_xyxy(
                    xyxy=np.tile(np.array([1.0, 1.0, 20.0, 10.0]), (count, 1)),
                    confidences=np.linspace(0.3, 0.9, count),
                    query_ids=np.arange(count, dtype=np.int64) % len(prompt.queries),
                    prompt=prompt,
                    image_size=ImageSize(width=image.width, height=image.height),
                )
            )
        return results


class ManualCall:
    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback: Callable[[], None] = callback
        self.is_cancelled: bool = False

    def cancel(self) -> None:
        self.is_cancelled = True


class ManualScheduler:
    def __init__(self) -> None:
        self._callbacks: SimpleQueue[Callable[[], None]] = SimpleQueue()
        self.delayed_calls: list[ManualCall] = []

    def dispatch(self, callback: Callable[[], None]) -> None:
        self._callbacks.put(callback)

    def call_later(self, delay_seconds: float, callback: Callable[[], None]) -> ManualCall:
        call: ManualCall = ManualCall(callback)
        self.delayed_calls.append(call)
        return call

    def run_blocking[ResultT](
        self,
        task: Callable[[], ResultT],
        on_done: Callable[[ResultT], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        try:
            result: ResultT = task()
        except Exception as error:  # noqa: BLE001
            self.dispatch(partial(on_error, error))
            return
        self.dispatch(partial(on_done, result))

    def run_delayed_calls(self) -> None:
        calls: list[ManualCall] = self.delayed_calls
        self.delayed_calls = []
        for call in calls:
            if not call.is_cancelled:
                call.callback()

    def pump_until(self, condition: Callable[[], bool], timeout_seconds: float = 10.0) -> None:
        deadline: float = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                self._callbacks.get(timeout=0.02)()
            except Empty:
                if condition():
                    return
        assert condition()


class RecordingObserver:
    def __init__(self) -> None:
        self.topics: list[frozenset[WorkspaceTopic]] = []
        self.notices: list[Notice] = []

    def on_changed(self, topics: frozenset[WorkspaceTopic]) -> None:
        self.topics.append(topics)

    def on_notice(self, notice: Notice) -> None:
        self.notices.append(notice)


@pytest.fixture
def image_directory(tmp_path: Path) -> Path:
    directory: Path = tmp_path / "images"
    directory.mkdir()
    for index, width in enumerate((32, 64, 96)):
        Image.new("RGB", (width, 16)).save(directory / f"image{index}.png")
    return directory


@pytest.fixture
def stores(tmp_path: Path) -> WorkspaceStores:
    data_directory: Path = tmp_path / "data"
    return WorkspaceStores(
        class_list_store=ClassListStore(data_directory),
        class_set_store=ClassSetStore(data_directory),
        result_store=ResultStore(data_directory),
        class_threshold_store=ClassThresholdStore(data_directory),
        session_store=SessionStore(data_directory),
        upload_store=UploadStore(data_directory),
    )


@pytest.fixture
def model_selector() -> ModelSelector:
    return ModelSelector(
        PresetCatalog.from_package(), DeviceAvailability(is_cuda_available=False, is_mps_available=False)
    )


@pytest.fixture
def scheduler() -> ManualScheduler:
    return ManualScheduler()


@pytest.fixture
def detector(model_selector: ModelSelector) -> WidthCountingDetector:
    return WidthCountingDetector(model_selector.settings_of(model_selector.default_selection()))


@pytest.fixture
def workspace(
    model_selector: ModelSelector, stores: WorkspaceStores, scheduler: ManualScheduler, detector: WidthCountingDetector
) -> Iterator[Workspace]:
    session: DetectorSession = DetectorSession()
    session._detector = detector
    created: Workspace = Workspace(model_selector, stores, scheduler, session)
    created.edit_classes(lambda bench: bench.set_classes((ClassDefinition.named("cat"), ClassDefinition.named("dog"))))
    yield created
    created.shutdown()


@pytest.fixture
def wait_until_idle(workspace: Workspace, scheduler: ManualScheduler) -> Callable[[], None]:
    def wait() -> None:
        scheduler.pump_until(lambda: not workspace.is_busy and workspace.background_image_path is None)

    return wait


@pytest.fixture
def run_delayed_calls(scheduler: ManualScheduler) -> Callable[[], None]:
    return scheduler.run_delayed_calls


@pytest.fixture
def observer(workspace: Workspace) -> RecordingObserver:
    recording_observer: RecordingObserver = RecordingObserver()
    workspace.add_observer(recording_observer)
    return recording_observer


@pytest.fixture
def notices(observer: RecordingObserver) -> list[Notice]:
    return observer.notices


@pytest.fixture
def fail_width(detector: WidthCountingDetector) -> Callable[[int], None]:
    def fail(width: int) -> None:
        detector.failing_widths = frozenset({width})

    return fail
