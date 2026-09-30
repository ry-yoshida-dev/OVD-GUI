import time
from collections.abc import Iterator, Sequence
from pathlib import Path
from threading import Event
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
from ovd_gui.gui.execution import DetectionRunner
from ovd_gui.vocabulary import ClassDefinition
from ovd_gui.workspace import BatchJob

_FAILING_WIDTH: int = 13


class GatedDetector(OpenVocabularyDetector):
    BACKEND: ClassVar[DetectorBackend] = DetectorBackend.YOLOE

    def __init__(self, settings: DetectorSettings) -> None:
        super().__init__(settings)
        self.gate: Event = Event()
        self.detected_widths: list[int] = []

    def _detect_mini_batch(self, images: Sequence[Image.Image], prompt: Prompt) -> list[DetectionResult]:
        if not self.gate.wait(timeout=10.0):
            raise RuntimeError("gate was never opened")
        results: list[DetectionResult] = []
        for image in images:
            if image.width == _FAILING_WIDTH:
                raise ValueError("unsupported image")
            self.detected_widths.append(image.width)
            results.append(DetectionResult.empty(prompt, ImageSize(width=image.width, height=image.height)))
        return results


class RunnerRecorder:
    def __init__(self, runner: DetectionRunner) -> None:
        self.busy_states: list[bool] = []
        self.succeeded: list[DetectionOutcome] = []
        self.failed: list[DetectionFailure] = []
        self.background_succeeded: list[DetectionOutcome] = []
        self.background_failed: list[tuple[DetectionRequest, DetectionFailure]] = []
        self.batch_started: list[BatchJob] = []
        self.batch_progress: list[tuple[int, int]] = []
        self.batch_detected: list[Path] = []
        self.batch_finished: list[tuple[BatchJob, BatchDetectionSummary]] = []
        runner.busy_changed.connect(self.busy_states.append)
        runner.succeeded.connect(self.succeeded.append)
        runner.failed.connect(self.failed.append)
        runner.background_succeeded.connect(self.background_succeeded.append)
        runner.background_failed.connect(self.record_background_failure)
        runner.batch_started.connect(self.batch_started.append)
        runner.batch_progressed.connect(self.record_batch_progress)
        runner.batch_image_detected.connect(self.record_batch_detection)
        runner.batch_finished.connect(self.record_batch_finish)

    def record_background_failure(self, request: DetectionRequest, failure: DetectionFailure) -> None:
        self.background_failed.append((request, failure))

    def record_batch_progress(self, job: BatchJob, processed_count: int, total_count: int) -> None:
        self.batch_progress.append((processed_count, total_count))

    def record_batch_detection(self, job: BatchJob, image_path: Path, result: DetectionResult) -> None:
        self.batch_detected.append(image_path)

    def record_batch_finish(self, job: BatchJob, summary: BatchDetectionSummary) -> None:
        self.batch_finished.append((job, summary))


@pytest.fixture
def settings() -> DetectorSettings:
    return DetectorSettings(
        backend=DetectorBackend.YOLOE,
        weights_path="yoloe-26s-seg.pt",
        thresholds=DetectionThresholds(confidence_threshold=0.25, nms_iou_threshold=0.7),
    )


@pytest.fixture
def detector(settings: DetectorSettings) -> GatedDetector:
    return GatedDetector(settings)


@pytest.fixture
def runner(application: QApplication, detector: GatedDetector) -> Iterator[DetectionRunner]:
    detection_runner: DetectionRunner = DetectionRunner()
    detection_runner._worker._session._detector = detector
    yield detection_runner
    detector.gate.set()
    detection_runner.shutdown()


@pytest.fixture
def recorder(runner: DetectionRunner) -> RunnerRecorder:
    return RunnerRecorder(runner)


def _labeled_prompt() -> LabeledPrompt:
    return ReferenceBoard().build_prompt((ClassDefinition.named("cat"),), frozenset({PromptKind.TEXT}))


def _request(settings: DetectorSettings, directory: Path, name: str, width: int) -> DetectionRequest:
    image_path: Path = directory / name
    if not image_path.exists():
        Image.new("RGB", (width, 16)).save(image_path)
    return DetectionRequest(settings=settings, image_path=image_path, labeled_prompt=_labeled_prompt())


def _batch_job(settings: DetectorSettings, directory: Path, widths: Sequence[int]) -> BatchJob:
    image_paths: list[Path] = []
    for width in widths:
        image_path: Path = directory / f"image{width}.png"
        Image.new("RGB", (width, 16)).save(image_path)
        image_paths.append(image_path)
    return BatchJob.detect_all(
        BatchDetectionRequest(settings=settings, labeled_prompt=_labeled_prompt(), image_paths=tuple(image_paths))
    )


def _release_and_wait(application: QApplication, runner: DetectionRunner, detector: GatedDetector) -> None:
    detector.gate.set()
    deadline: float = time.monotonic() + 10.0
    while not runner.is_idle and time.monotonic() < deadline:
        application.processEvents()
    assert runner.is_idle


def _widths(outcomes: Sequence[DetectionOutcome]) -> list[int]:
    return [outcome.result.image_size.width for outcome in outcomes]


def test_background_detection_is_reported_apart_without_marking_the_runner_busy(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    recorder: RunnerRecorder,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    runner.detect_in_background(_request(settings, tmp_path, "a.png", 32))
    assert not runner.is_busy
    assert not runner.is_idle
    _release_and_wait(application, runner, detector)
    assert _widths(recorder.background_succeeded) == [32]
    assert recorder.succeeded == []
    assert recorder.busy_states == []


def test_only_the_latest_waiting_background_request_is_detected(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    recorder: RunnerRecorder,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    runner.detect_in_background(_request(settings, tmp_path, "a.png", 32))
    runner.detect_in_background(_request(settings, tmp_path, "b.png", 64))
    runner.detect_in_background(_request(settings, tmp_path, "c.png", 96))
    _release_and_wait(application, runner, detector)
    assert detector.detected_widths == [32, 96]
    assert _widths(recorder.background_succeeded) == [32, 96]


def test_background_request_for_the_detection_in_progress_drops_the_waiting_one(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    recorder: RunnerRecorder,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    runner.detect_in_background(_request(settings, tmp_path, "a.png", 32))
    runner.detect_in_background(_request(settings, tmp_path, "b.png", 64))
    runner.detect_in_background(_request(settings, tmp_path, "a.png", 32))
    _release_and_wait(application, runner, detector)
    assert detector.detected_widths == [32]


def test_background_request_with_another_profile_is_not_the_detection_in_progress(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    stricter_settings: DetectorSettings = DetectorSettings(
        backend=settings.backend,
        weights_path=settings.weights_path,
        thresholds=DetectionThresholds(confidence_threshold=0.5, nms_iou_threshold=0.7),
    )
    runner.detect_in_background(_request(settings, tmp_path, "a.png", 32))
    runner.detect_in_background(_request(stricter_settings, tmp_path, "a.png", 32))
    _release_and_wait(application, runner, detector)
    assert detector.detected_widths == [32, 32]


def test_foreground_detection_waits_for_the_background_one_and_discards_waiting_background_requests(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    recorder: RunnerRecorder,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    runner.detect_in_background(_request(settings, tmp_path, "a.png", 32))
    runner.detect_in_background(_request(settings, tmp_path, "b.png", 64))
    runner.detect(_request(settings, tmp_path, "c.png", 96))
    assert runner.is_busy
    _release_and_wait(application, runner, detector)
    assert detector.detected_widths == [32, 96]
    assert _widths(recorder.background_succeeded) == [32]
    assert _widths(recorder.succeeded) == [96]
    assert recorder.busy_states == [True, False]


def test_second_foreground_run_is_rejected_and_background_requests_are_ignored_while_busy(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    recorder: RunnerRecorder,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    runner.detect(_request(settings, tmp_path, "a.png", 32))
    with pytest.raises(RuntimeError, match="already running"):
        runner.detect(_request(settings, tmp_path, "b.png", 64))
    with pytest.raises(RuntimeError, match="already running"):
        runner.detect_batch(_batch_job(settings, tmp_path, (40,)))
    runner.detect_in_background(_request(settings, tmp_path, "c.png", 96))
    _release_and_wait(application, runner, detector)
    assert detector.detected_widths == [32]
    assert recorder.batch_started == []
    assert recorder.busy_states == [True, False]


def test_failed_background_detection_names_its_request_and_the_waiting_request_follows(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    recorder: RunnerRecorder,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    failing_request: DetectionRequest = _request(settings, tmp_path, "broken.png", _FAILING_WIDTH)
    runner.detect_in_background(failing_request)
    runner.detect_in_background(_request(settings, tmp_path, "b.png", 64))
    _release_and_wait(application, runner, detector)
    assert len(recorder.background_failed) == 1
    failed_request, failure = recorder.background_failed[0]
    assert failed_request is failing_request
    assert failure.kind is DetectionFailureKind.DETECTION_ERROR
    assert "ValueError" in failure.message
    assert _widths(recorder.background_succeeded) == [64]
    assert recorder.failed == []


def test_failed_foreground_detection_is_reported_and_frees_the_runner(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    recorder: RunnerRecorder,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    runner.detect(_request(settings, tmp_path, "broken.png", _FAILING_WIDTH))
    _release_and_wait(application, runner, detector)
    assert len(recorder.failed) == 1
    assert recorder.failed[0].kind is DetectionFailureKind.DETECTION_ERROR
    assert "ValueError" in recorder.failed[0].message
    assert recorder.background_failed == []
    assert recorder.busy_states == [True, False]


def test_batch_reports_its_progress_and_detections_under_its_job(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    recorder: RunnerRecorder,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    job: BatchJob = _batch_job(settings, tmp_path, (40, 48))
    runner.detect_batch(job)
    assert recorder.batch_started == [job]
    assert runner.is_busy
    _release_and_wait(application, runner, detector)
    assert recorder.batch_detected == list(job.request.image_paths)
    assert recorder.batch_progress[-1] == (2, 2)
    assert recorder.batch_finished == [
        (job, BatchDetectionSummary(detected_count=2, unreadable_paths=(), is_cancelled=False))
    ]
    assert recorder.busy_states == [True, False]
    assert not runner.prioritize(job.request.image_paths[0])


def test_batch_waits_for_the_background_detection_and_detects_a_prioritized_image_first(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    recorder: RunnerRecorder,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    job: BatchJob = _batch_job(settings, tmp_path, (40, 48, 56))
    runner.detect_in_background(_request(settings, tmp_path, "a.png", 32))
    runner.detect_batch(job)
    assert runner.prioritize(job.request.image_paths[2])
    _release_and_wait(application, runner, detector)
    assert detector.detected_widths == [32, 56, 40, 48]
    assert _widths(recorder.background_succeeded) == [32]


def test_cancelled_batch_is_reported_as_cancelled(
    application: QApplication,
    runner: DetectionRunner,
    detector: GatedDetector,
    recorder: RunnerRecorder,
    settings: DetectorSettings,
    tmp_path: Path,
) -> None:
    job: BatchJob = _batch_job(settings, tmp_path, (40, 48))
    runner.detect_in_background(_request(settings, tmp_path, "a.png", 32))
    runner.detect_batch(job)
    runner.cancel_batch()
    _release_and_wait(application, runner, detector)
    assert detector.detected_widths == [32]
    assert recorder.batch_finished == [
        (job, BatchDetectionSummary(detected_count=0, unreadable_paths=(), is_cancelled=True))
    ]
    assert recorder.busy_states == [True, False]
