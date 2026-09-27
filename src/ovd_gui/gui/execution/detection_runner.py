from pathlib import Path

from open_vocabulary_detector import DetectionResult
from PySide6.QtCore import QObject, QThread, Signal

from ...detection import BatchDetectionRequest, BatchDetectionSummary, DetectionOutcome, DetectionRequest
from .batch_job import BatchJob
from .detection_worker import DetectionWorker


class DetectionRunner(QObject):
    """
    Owner of the worker thread: starts one detection or one batch at a time and reports how it ends.

    The runner lives on the GUI thread; requests are queued to a ``DetectionWorker`` on its own ``QThread``, and
    the worker's signals come back to the runner, which tracks whether a run is in progress and which batch job
    the results belong to. Call ``shutdown`` before the application quits.

    Signals
    -------
    busy_changed : Signal(bool)
        A run started or ended.
    status_changed : Signal(str)
        Progress message of the worker.
    succeeded : Signal(DetectionOutcome)
        A single detection finished.
    failed : Signal(str)
        Error message of a failed single detection.
    batch_started : Signal(BatchJob)
        A batch was queued to the worker.
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
        Whether a detection or batch is in progress.

        Returns
        -------
        bool
            True from a start until its outcome is reported.
        """
        return self._is_busy

    def detect(self, request: DetectionRequest) -> None:
        """
        Queue one detection to the worker.

        Parameters
        ----------
        request : DetectionRequest
            Settings, image and prompt.

        Raises
        ------
        RuntimeError
            If a run is already in progress.
        """
        self._start()
        self._detection_queued.emit(request)

    def detect_batch(self, job: BatchJob) -> None:
        """
        Queue a batch to the worker.

        Parameters
        ----------
        job : BatchJob
            Batch request and its purpose.

        Raises
        ------
        RuntimeError
            If a run is already in progress.
        """
        self._start()
        self._job = job
        self.batch_started.emit(job)
        self._batch_queued.emit(job.request)

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
        self.cancel_batch()
        self._thread.quit()
        self._thread.wait()

    def _start(self) -> None:
        if self._is_busy:
            raise RuntimeError("A detection is already running.")
        self._set_busy(True)

    def _set_busy(self, is_busy: bool) -> None:
        self._is_busy = is_busy
        self.busy_changed.emit(is_busy)

    def _finish_batch(self) -> BatchJob | None:
        job: BatchJob | None = self._job
        self._job = None
        self._set_busy(False)
        return job

    def _on_succeeded(self, outcome: DetectionOutcome) -> None:
        self._set_busy(False)
        self.succeeded.emit(outcome)

    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        self.failed.emit(message)

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

    def _on_batch_failed(self, message: str) -> None:
        job: BatchJob | None = self._finish_batch()
        if job is not None:
            self.batch_failed.emit(job, message)
