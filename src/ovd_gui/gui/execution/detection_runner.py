from pathlib import Path

from open_vocabulary_detector import DetectionResult
from PySide6.QtCore import QObject, QThread, Signal

from ...detection import (
    BatchDetectionRequest,
    BatchDetectionSummary,
    DetectionOutcome,
    DetectionRequest,
    DetectorProfile,
)
from .batch_job import BatchJob
from .detection_worker import DetectionWorker


class DetectionRunner(QObject):
    """
    Owner of the worker thread: runs the detections the user asked for, and background detections in between.

    The runner lives on the GUI thread; requests are queued to a ``DetectionWorker`` on its own ``QThread``, and
    the worker's signals come back to the runner, which tracks which run is in progress and which batch job the
    results belong to. Call ``shutdown`` before the application quits.

    A run the user asked for (``detect`` or ``detect_batch``) is a foreground run: only one at a time, and
    ``is_busy`` is True from its request until its outcome is reported. A background detection
    (``detect_in_background``) never makes the runner busy and always yields: it is ignored while a foreground run
    is requested, a foreground run requested meanwhile starts as soon as the image being inferred is done, and of
    the background detections requested meanwhile only the latest is kept.

    Signals
    -------
    busy_changed : Signal(bool)
        A foreground run was requested or its outcome was reported.
    status_changed : Signal(str)
        Progress message of the worker.
    succeeded : Signal(DetectionOutcome)
        A single foreground detection finished.
    failed : Signal(str)
        Error message of a failed single foreground detection.
    background_succeeded : Signal(DetectionOutcome)
        A background detection finished.
    background_failed : Signal(DetectionRequest, str)
        A background detection failed, with the error message.
    batch_started : Signal(BatchJob)
        A batch was requested.
    batch_progressed : Signal(BatchJob, int, int)
        Images processed so far and the total of the running batch.
    batch_image_detected : Signal(BatchJob, Path, DetectionResult)
        Detections of one image of the running batch.
    batch_finished : Signal(BatchJob, BatchDetectionSummary)
        The batch completed or was cancelled.
    batch_failed : Signal(BatchJob, str)
        Error message of a batch stopped by a loading or inference error.
    """

    busy_changed: Signal = Signal(bool)
    status_changed: Signal = Signal(str)
    succeeded: Signal = Signal(DetectionOutcome)
    failed: Signal = Signal(str)
    background_succeeded: Signal = Signal(DetectionOutcome)
    background_failed: Signal = Signal(DetectionRequest, str)
    batch_started: Signal = Signal(BatchJob)
    batch_progressed: Signal = Signal(BatchJob, int, int)
    batch_image_detected: Signal = Signal(BatchJob, Path, DetectionResult)
    batch_finished: Signal = Signal(BatchJob, BatchDetectionSummary)
    batch_failed: Signal = Signal(BatchJob, str)

    _detection_queued: Signal = Signal(DetectionRequest)
    _batch_queued: Signal = Signal(BatchDetectionRequest)

    def __init__(self, parent: QObject | None = None) -> None:
        """
        Parameters
        ----------
        parent : QObject | None, optional
            Parent object.
        """
        super().__init__(parent)
        self._is_busy: bool = False
        self._job: BatchJob | None = None
        self._background_request: DetectionRequest | None = None
        self._waiting_background_request: DetectionRequest | None = None
        self._waiting_foreground_run: DetectionRequest | BatchJob | None = None
        self._thread: QThread = QThread(self)
        self._worker: DetectionWorker = DetectionWorker()
        self._worker.moveToThread(self._thread)
        self._detection_queued.connect(self._worker.run)
        self._batch_queued.connect(self._worker.run_batch)
        self._worker.status_changed.connect(self.status_changed)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._worker.batch_progressed.connect(self._on_batch_progressed)
        self._worker.image_detected.connect(self._on_image_detected)
        self._worker.batch_finished.connect(self._on_batch_finished)
        self._worker.batch_failed.connect(self._on_batch_failed)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    @property
    def is_busy(self) -> bool:
        """
        Whether a foreground detection or batch is in progress.

        Returns
        -------
        bool
            True from a foreground request until its outcome is reported.
        """
        return self._is_busy

    @property
    def is_idle(self) -> bool:
        """
        Whether the worker has nothing to do, in the foreground or the background.

        Returns
        -------
        bool
            True when no run is in progress or waiting.
        """
        return not self._is_busy and self._background_request is None

    def detect(self, request: DetectionRequest) -> None:
        """
        Run one foreground detection, after the background detection in progress if any.

        Parameters
        ----------
        request : DetectionRequest
            Settings, image and prompt.

        Raises
        ------
        RuntimeError
            If a foreground run is already in progress.
        """
        self._start()
        self._queue_foreground(request)

    def detect_batch(self, job: BatchJob) -> None:
        """
        Run a foreground batch, after the background detection in progress if any.

        Parameters
        ----------
        job : BatchJob
            Batch request and its purpose.

        Raises
        ------
        RuntimeError
            If a foreground run is already in progress.
        """
        self._start()
        self._job = job
        self.batch_started.emit(job)
        self._queue_foreground(job)

    def detect_in_background(self, request: DetectionRequest) -> None:
        """
        Detect when no foreground run needs the worker, replacing a background detection still waiting.

        Ignored while a foreground run is in progress, and when the same image is already being inferred with the
        same detector profile.

        Parameters
        ----------
        request : DetectionRequest
            Settings, image and prompt.
        """
        if self._is_busy:
            return
        if self._background_request is None:
            self._send_background(request)
            return
        is_in_progress: bool = self._is_same_detection(request, self._background_request)
        self._waiting_background_request = None if is_in_progress else request

    def prioritize(self, image_path: Path) -> bool:
        """
        Detect an image of the running batch before its other images.

        Parameters
        ----------
        image_path : Path
            Image to detect next.

        Returns
        -------
        bool
            True when a batch is running and the image is still waiting in it.
        """
        return self._job is not None and self._job.request.prioritize(image_path)

    def cancel_batch(self) -> None:
        """
        Ask the running batch, if any, to stop before its next image.
        """
        if self._job is not None:
            self._job.request.cancel()

    def shutdown(self) -> None:
        """
        Cancel the running batch and stop the worker thread, waiting for the current image to finish.
        """
        self._waiting_background_request = None
        self.cancel_batch()
        self._thread.quit()
        self._thread.wait()

    @staticmethod
    def _is_same_detection(request: DetectionRequest, other: DetectionRequest) -> bool:
        return request.image_path == other.image_path and DetectorProfile.of(request.settings) == DetectorProfile.of(
            other.settings
        )

    def _start(self) -> None:
        if self._is_busy:
            raise RuntimeError("A detection is already running.")
        self._set_busy(True)

    def _set_busy(self, is_busy: bool) -> None:
        self._is_busy = is_busy
        self.busy_changed.emit(is_busy)

    def _queue_foreground(self, run: DetectionRequest | BatchJob) -> None:
        self._waiting_background_request = None
        if self._background_request is None:
            self._send_foreground(run)
        else:
            self._waiting_foreground_run = run

    def _send_foreground(self, run: DetectionRequest | BatchJob) -> None:
        match run:
            case BatchJob():
                self._batch_queued.emit(run.request)
            case DetectionRequest():
                self._detection_queued.emit(run)

    def _send_background(self, request: DetectionRequest) -> None:
        self._background_request = request
        self._detection_queued.emit(request)

    def _finish_background(self) -> DetectionRequest:
        request: DetectionRequest | None = self._background_request
        if request is None:
            raise RuntimeError("No background detection is in progress.")
        self._background_request = None
        return request

    def _send_waiting_run(self) -> None:
        foreground_run: DetectionRequest | BatchJob | None = self._waiting_foreground_run
        background_request: DetectionRequest | None = self._waiting_background_request
        self._waiting_foreground_run = None
        self._waiting_background_request = None
        if foreground_run is not None:
            self._send_foreground(foreground_run)
        elif background_request is not None:
            self._send_background(background_request)

    def _finish_batch(self) -> BatchJob | None:
        job: BatchJob | None = self._job
        self._job = None
        return job

    def _on_succeeded(self, outcome: DetectionOutcome) -> None:
        if self._background_request is not None:
            self._finish_background()
            self.background_succeeded.emit(outcome)
            self._send_waiting_run()
            return
        self.succeeded.emit(outcome)
        self._set_busy(False)

    def _on_failed(self, message: str) -> None:
        if self._background_request is not None:
            request: DetectionRequest = self._finish_background()
            self.background_failed.emit(request, message)
            self._send_waiting_run()
            return
        self.failed.emit(message)
        self._set_busy(False)

    def _on_batch_progressed(self, processed_count: int, total_count: int) -> None:
        if self._job is not None:
            self.batch_progressed.emit(self._job, processed_count, total_count)

    def _on_image_detected(self, image_path: Path, result: DetectionResult) -> None:
        if self._job is not None:
            self.batch_image_detected.emit(self._job, image_path, result)

    def _on_batch_finished(self, summary: BatchDetectionSummary) -> None:
        job: BatchJob | None = self._finish_batch()
        if job is not None:
            self.batch_finished.emit(job, summary)
        self._set_busy(False)

    def _on_batch_failed(self, message: str) -> None:
        job: BatchJob | None = self._finish_batch()
        if job is not None:
            self.batch_failed.emit(job, message)
        self._set_busy(False)
