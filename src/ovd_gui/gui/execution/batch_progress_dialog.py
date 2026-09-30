from PySide6.QtCore import Qt
from PySide6.QtWidgets import QProgressDialog, QWidget

from ...detection import BatchDetectionSummary
from ...workspace import BatchJob
from .detection_runner import DetectionRunner


class BatchProgressDialog(QProgressDialog):
    """
    Window-modal progress of a blocking batch running on a ``DetectionRunner``, with a Cancel button.

    The dialog follows the runner by itself: it opens when a blocking batch starts, advances with it, and closes when
    the batch finishes or fails. Cancel asks the runner to stop the batch. Background batches are left to
    ``RunProgressIndicator``.
    """

    def __init__(self, runner: DetectionRunner, parent: QWidget) -> None:
        """
        Parameters
        ----------
        runner : DetectionRunner
            Runner whose blocking batches are shown.
        parent : QWidget
            Window blocked while a blocking batch runs.
        """
        super().__init__(parent)
        self.setCancelButtonText("Cancel")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumDuration(0)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.canceled.connect(runner.cancel_batch)
        runner.batch_started.connect(self._on_batch_started)
        runner.batch_progressed.connect(self._on_batch_progressed)
        runner.batch_finished.connect(self._on_batch_finished)
        runner.batch_failed.connect(self._on_batch_failed)
        self.reset()

    def _on_batch_started(self, job: BatchJob) -> None:
        if not job.purpose.is_blocking:
            return
        total_count: int = len(job.request.image_paths)
        self.setWindowTitle(job.purpose.title)
        self.setLabelText(job.purpose.progress_text(0, total_count))
        self.setMaximum(total_count)
        self.setValue(0)

    def _on_batch_progressed(self, job: BatchJob, processed_count: int, total_count: int) -> None:
        if not job.purpose.is_blocking:
            return
        self.setLabelText(job.purpose.progress_text(processed_count, total_count))
        self.setValue(processed_count)

    def _on_batch_finished(self, job: BatchJob, summary: BatchDetectionSummary) -> None:
        self._close_progress()

    def _on_batch_failed(self, job: BatchJob, message: str) -> None:
        self._close_progress()

    def _close_progress(self) -> None:
        self.hide()
        self.reset()
