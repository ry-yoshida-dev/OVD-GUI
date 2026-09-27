from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

import pytest
from open_vocabulary_detector import (
    DetectionResult,
    DetectionThresholds,
    DetectorBackend,
    DetectorSettings,
    ImageSize,
    OpenVocabularyDetector,
    Prompt,
    PromptKind,
)
from PIL import Image
from PySide6.QtWidgets import QApplication

from ovd_gui.detection import (
    BatchDetectionRequest,
    BatchDetectionSummary,
    DetectionFailure,
    DetectionFailureKind,
    DetectionOutcome,
    DetectionRequest,
    LabeledPrompt,
    ReferenceBoard,
)
from ovd_gui.gui.execution import DetectionWorker
from ovd_gui.vocabulary import ClassDefinition


class EmptyResultDetector(OpenVocabularyDetector):
    BACKEND: ClassVar[DetectorBackend] = DetectorBackend.YOLOE

    def _detect_mini_batch(self, images: Sequence[Image.Image], prompt: Prompt) -> list[DetectionResult]:
        return [DetectionResult.empty(prompt, ImageSize(width=image.width, height=image.height)) for image in images]


class IndexErrorDetector(OpenVocabularyDetector):
    BACKEND: ClassVar[DetectorBackend] = DetectorBackend.YOLOE

    def _detect_mini_batch(self, images: Sequence[Image.Image], prompt: Prompt) -> list[DetectionResult]:
        raise IndexError("query index out of range")


class RunRecorder:
    def __init__(self, worker: DetectionWorker) -> None:
        self.outcomes: list[DetectionOutcome] = []
        self.failures: list[DetectionFailure] = []
        worker.succeeded.connect(self.outcomes.append)
        worker.failed.connect(self.failures.append)


class BatchRecorder:
    def __init__(self, worker: DetectionWorker) -> None:
        self.detected: list[tuple[Path, DetectionResult]] = []
        self.summaries: list[BatchDetectionSummary] = []
        self.failures: list[str] = []
        worker.image_detected.connect(self.record_detection)
        worker.batch_finished.connect(self.summaries.append)
        worker.batch_failed.connect(self.failures.append)

    def record_detection(self, image_path: Path, result: DetectionResult) -> None:
        self.detected.append((image_path, result))


def _labeled_prompt() -> LabeledPrompt:
    return ReferenceBoard().build_prompt((ClassDefinition.named("cat"),), frozenset({PromptKind.TEXT}))


@pytest.fixture
def settings() -> DetectorSettings:
    return DetectorSettings(
        backend=DetectorBackend.YOLOE,
        weights_path="yoloe-26s-seg.pt",
        thresholds=DetectionThresholds(confidence_threshold=0.25, nms_iou_threshold=0.7),
    )


@pytest.fixture
def worker(application: QApplication, settings: DetectorSettings) -> DetectionWorker:
    detection_worker: DetectionWorker = DetectionWorker()
    detection_worker._session._detector = EmptyResultDetector(settings)
    return detection_worker


def _image(directory: Path, name: str) -> Path:
    path: Path = directory / name
    Image.new("RGB", (32, 16)).save(path)
    return path


def test_request_needs_images(settings: DetectorSettings) -> None:
    with pytest.raises(ValueError, match="image_paths"):
        BatchDetectionRequest(settings=settings, labeled_prompt=_labeled_prompt(), image_paths=())


def test_batch_detects_every_image_and_skips_unreadable_files(
    worker: DetectionWorker, settings: DetectorSettings, tmp_path: Path
) -> None:
    broken_path: Path = tmp_path / "broken.jpg"
    broken_path.write_bytes(b"not an image")
    image_paths: tuple[Path, ...] = (_image(tmp_path, "a.png"), broken_path, _image(tmp_path, "b.png"))
    recorder: BatchRecorder = BatchRecorder(worker)
    worker.run_batch(
        BatchDetectionRequest(settings=settings, labeled_prompt=_labeled_prompt(), image_paths=image_paths)
    )
    assert [path for path, _ in recorder.detected] == [image_paths[0], image_paths[2]]
    assert recorder.detected[0][1].image_size == ImageSize(width=32, height=16)
    assert recorder.summaries == [
        BatchDetectionSummary(detected_count=2, unreadable_paths=(broken_path,), is_cancelled=False)
    ]
    assert recorder.failures == []


def test_cancelled_batch_stops_before_the_next_image(
    worker: DetectionWorker, settings: DetectorSettings, tmp_path: Path
) -> None:
    request: BatchDetectionRequest = BatchDetectionRequest(
        settings=settings,
        labeled_prompt=_labeled_prompt(),
        image_paths=(_image(tmp_path, "a.png"), _image(tmp_path, "b.png")),
    )
    recorder: BatchRecorder = BatchRecorder(worker)

    def cancel_after_first_image(image_path: Path, result: DetectionResult) -> None:
        request.cancel()

    worker.image_detected.connect(cancel_after_first_image)
    worker.run_batch(request)
    assert len(recorder.detected) == 1
    assert recorder.summaries == [BatchDetectionSummary(detected_count=1, unreadable_paths=(), is_cancelled=True)]


def test_image_prioritized_during_a_batch_is_detected_next(
    worker: DetectionWorker, settings: DetectorSettings, tmp_path: Path
) -> None:
    image_paths: tuple[Path, ...] = tuple(_image(tmp_path, name) for name in ("a.png", "b.png", "c.png"))
    request: BatchDetectionRequest = BatchDetectionRequest(
        settings=settings, labeled_prompt=_labeled_prompt(), image_paths=image_paths
    )
    recorder: BatchRecorder = BatchRecorder(worker)

    def prioritize_last_image(image_path: Path, result: DetectionResult) -> None:
        request.prioritize(image_paths[2])

    worker.image_detected.connect(prioritize_last_image)
    worker.run_batch(request)
    assert [path.name for path, _ in recorder.detected] == ["a.png", "c.png", "b.png"]
    assert recorder.summaries == [BatchDetectionSummary(detected_count=3, unreadable_paths=(), is_cancelled=False)]


def test_single_detection_reads_the_image_file_on_the_worker(
    worker: DetectionWorker, settings: DetectorSettings, tmp_path: Path
) -> None:
    recorder: RunRecorder = RunRecorder(worker)
    worker.run(
        DetectionRequest(settings=settings, image_path=_image(tmp_path, "a.png"), labeled_prompt=_labeled_prompt())
    )
    assert [outcome.result.image_size for outcome in recorder.outcomes] == [ImageSize(width=32, height=16)]
    assert recorder.failures == []


def test_unreadable_image_file_is_reported_as_unreadable(
    worker: DetectionWorker, settings: DetectorSettings, tmp_path: Path
) -> None:
    broken_path: Path = tmp_path / "broken.jpg"
    broken_path.write_bytes(b"not an image")
    recorder: RunRecorder = RunRecorder(worker)
    worker.run(DetectionRequest(settings=settings, image_path=broken_path, labeled_prompt=_labeled_prompt()))
    assert recorder.outcomes == []
    assert [failure.kind for failure in recorder.failures] == [DetectionFailureKind.UNREADABLE_IMAGE]


def test_unexpected_error_of_a_single_detection_is_reported(
    worker: DetectionWorker, settings: DetectorSettings, tmp_path: Path
) -> None:
    worker._session._detector = IndexErrorDetector(settings)
    recorder: RunRecorder = RunRecorder(worker)
    worker.run(
        DetectionRequest(settings=settings, image_path=_image(tmp_path, "a.png"), labeled_prompt=_labeled_prompt())
    )
    assert recorder.failures == [
        DetectionFailure(kind=DetectionFailureKind.DETECTION_ERROR, message="IndexError: query index out of range")
    ]


def test_unexpected_error_stops_the_batch_and_is_reported(
    worker: DetectionWorker, settings: DetectorSettings, tmp_path: Path
) -> None:
    worker._session._detector = IndexErrorDetector(settings)
    recorder: BatchRecorder = BatchRecorder(worker)
    worker.run_batch(
        BatchDetectionRequest(
            settings=settings, labeled_prompt=_labeled_prompt(), image_paths=(_image(tmp_path, "a.png"),)
        )
    )
    assert recorder.failures == ["a.png: IndexError: query index out of range"]
    assert recorder.summaries == []
