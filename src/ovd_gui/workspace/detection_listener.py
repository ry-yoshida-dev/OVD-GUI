from pathlib import Path
from typing import Protocol

from open_vocabulary_detector import DetectionResult

from ..detection import BatchDetectionSummary, DetectionFailure, DetectionOutcome, DetectionRequest
from .batch_job import BatchJob


class DetectionListener(Protocol):
    """
    Receiver of what a `DetectionEngine` reports, always called on the thread owning the engine.
    """

    def on_busy_changed(self, is_busy: bool) -> None:
        """
        A foreground run was requested or its outcome was reported.

        Parameters
        ----------
        is_busy : bool
            Whether a foreground run is in progress now.
        """
        ...

    def on_status_changed(self, message: str) -> None:
        """
        The worker reported what it is doing.

        Parameters
        ----------
        message : str
            Progress message, e.g. the model being loaded.
        """
        ...

    def on_succeeded(self, outcome: DetectionOutcome) -> None:
        """
        A single foreground detection finished.

        Parameters
        ----------
        outcome : DetectionOutcome
            Result with its request and timing.
        """
        ...

    def on_failed(self, failure: DetectionFailure) -> None:
        """
        A single foreground detection failed.

        Parameters
        ----------
        failure : DetectionFailure
            Why it failed.
        """
        ...

    def on_background_succeeded(self, outcome: DetectionOutcome) -> None:
        """
        A background detection finished.

        Parameters
        ----------
        outcome : DetectionOutcome
            Result with its request and timing.
        """
        ...

    def on_background_failed(self, request: DetectionRequest, failure: DetectionFailure) -> None:
        """
        A background detection failed.

        Parameters
        ----------
        request : DetectionRequest
            Request that failed.
        failure : DetectionFailure
            Why it failed.
        """
        ...

    def on_batch_progressed(self, job: BatchJob, processed_count: int, total_count: int) -> None:
        """
        The running batch moved on to its next image.

        Parameters
        ----------
        job : BatchJob
            Running batch.
        processed_count : int
            Images processed so far.
        total_count : int
            Images in the batch.
        """
        ...

    def on_batch_image_detected(self, job: BatchJob, image_path: Path, result: DetectionResult) -> None:
        """
        One image of the running batch was detected.

        Parameters
        ----------
        job : BatchJob
            Running batch.
        image_path : Path
            Detected image.
        result : DetectionResult
            Detections of the image.
        """
        ...

    def on_batch_finished(self, job: BatchJob, summary: BatchDetectionSummary) -> None:
        """
        The batch completed or was cancelled.

        Parameters
        ----------
        job : BatchJob
            Finished batch.
        summary : BatchDetectionSummary
            Detected count, skipped files and whether it was cancelled.
        """
        ...

    def on_batch_failed(self, job: BatchJob, message: str) -> None:
        """
        The batch stopped on a loading or inference error.

        Parameters
        ----------
        job : BatchJob
            Failed batch.
        message : str
            Error message.
        """
        ...
