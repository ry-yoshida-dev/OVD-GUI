from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QToolButton, QWidget

from ...workspace import BatchJob
from .detection_runner import DetectionRunner


class RunProgressIndicator(QWidget):
    """
    Compact progress of the run on a ``DetectionRunner``, meant for the status bar.

    The indicator follows the runner by itself: it is shown while a run is in progress and hidden afterwards. A single
    detection or a blocking batch shows a busy bar; a background batch shows its processed and total image counts and
    a Cancel button asking the runner to stop before the next image.
    """

    MAXIMUM_BAR_WIDTH = 200

    def __init__(self, runner: DetectionRunner, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        runner : DetectionRunner
            Runner whose runs are shown.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._runner: DetectionRunner = runner
        self._progress_bar: QProgressBar = QProgressBar()
        self._progress_bar.setMaximumWidth(self.MAXIMUM_BAR_WIDTH)
        self._cancel_button: QToolButton = QToolButton()
        self._cancel_button.setText("Cancel")
        self._cancel_button.setToolTip("Stop the batch before its next image")
        self._cancel_button.clicked.connect(self._on_cancel_clicked)

        layout: QHBoxLayout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._progress_bar)
        layout.addWidget(self._cancel_button)

        runner.busy_changed.connect(self._on_busy_changed)
        runner.batch_started.connect(self._on_batch_started)
        runner.batch_progressed.connect(self._on_batch_progressed)
        self._on_busy_changed(runner.is_busy)

    def _on_busy_changed(self, is_busy: bool) -> None:
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setTextVisible(False)
        self._cancel_button.setVisible(False)
        self.setVisible(is_busy)

    def _on_batch_started(self, job: BatchJob) -> None:
        if job.purpose.is_blocking:
            return
        self._progress_bar.setRange(0, len(job.request.image_paths))
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat(f"{job.purpose.title} %v/%m")
        self._progress_bar.setTextVisible(True)
        self._cancel_button.setEnabled(True)
        self._cancel_button.setVisible(True)

    def _on_batch_progressed(self, job: BatchJob, processed_count: int, total_count: int) -> None:
        if job.purpose.is_blocking:
            return
        self._progress_bar.setValue(processed_count)

    def _on_cancel_clicked(self) -> None:
        self._cancel_button.setEnabled(False)
        self._runner.cancel_batch()
