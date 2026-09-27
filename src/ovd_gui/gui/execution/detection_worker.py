from pathlib import Path

from open_vocabulary_detector import DetectionResult
from PySide6.QtCore import QObject, Signal, Slot

from ...detection import (
    BatchDetectionRequest,
    BatchDetectionSummary,
    DetectionFailure,
    DetectionFailureKind,
    DetectionOutcome,
    DetectionRequest,
    DetectorSession,
)
from ...media import LoadedImage


class DetectionWorker(QObject):
    """
    Runs image reading, model loading and inference off the GUI thread.

    Move the worker to a ``QThread`` and send it requests through queued signals connected to ``run``
    and ``run_batch``. Every request ends with exactly one of its outcome signals, whatever is raised while it runs,
    so the owner of the worker is never left waiting.

    Signals
    -------
    status_changed : Signal(str)
        Progress message.
    succeeded : Signal(DetectionOutcome)
        Detections of a finished request.
    failed : Signal(DetectionFailure)
        Why a request failed.
    batch_progressed : Signal(int, int)
        Images processed so far and the total of the running batch.
    image_detected : Signal(Path, DetectionResult)
        Detections of one image of the running batch.
    batch_finished : Signal(BatchDetectionSummary)
        The batch completed or was cancelled.
    batch_failed : Signal(str)
        Error message of a batch stopped by a loading or inference error.
    """

    status_changed: Signal = Signal(str)
    succeeded: Signal = Signal(DetectionOutcome)
    failed: Signal = Signal(DetectionFailure)
    batch_progressed: Signal = Signal(int, int)
    image_detected: Signal = Signal(Path, DetectionResult)
    batch_finished: Signal = Signal(BatchDetectionSummary)
    batch_failed: Signal = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._session: DetectorSession = DetectorSession()

    @Slot(DetectionRequest)
    def run(self, request: DetectionRequest) -> None:
        """
        Read the image, load the requested model if needed and detect.

        Every error is reported through ``failed`` so that the GUI keeps running: an error while reading the image
        file as ``UNREADABLE_IMAGE``, any error while loading the model or detecting as ``DETECTION_ERROR``.

        Parameters
        ----------
        request : DetectionRequest
            Settings, image file and prompt.
        """
        if not self._session.is_loaded_for(request.settings):
            self.status_changed.emit(f"Loading {request.settings.weights_path} ...")
        else:
            self.status_changed.emit("Detecting ...")
        try:
            loaded_image: LoadedImage = LoadedImage.open(request.image_path)
        except Exception as error:
            self.failed.emit(DetectionFailure.of(DetectionFailureKind.UNREADABLE_IMAGE, error))
            return
        try:
            outcome: DetectionOutcome = self._session.detect(request, loaded_image.image)
        except Exception as error:
            self.failed.emit(DetectionFailure.of(DetectionFailureKind.DETECTION_ERROR, error))
            return
        self.succeeded.emit(outcome)

    @Slot(BatchDetectionRequest)
    def run_batch(self, request: BatchDetectionRequest) -> None:
        """
        Detect in every image of the batch, loading the model once if needed.

        Image files that cannot be read are skipped; any error while loading the model or detecting stops the batch
        and is reported through ``batch_failed``. Cancellation and images prioritized from another thread are
        checked before each image.

        Parameters
        ----------
        request : BatchDetectionRequest
            Settings, prompt and image files.
        """
        total_count: int = len(request.image_paths)
        detected_count: int = 0
        unreadable_paths: list[Path] = []
        if not self._session.is_loaded_for(request.settings):
            self.status_changed.emit(f"Loading {request.settings.weights_path} ...")
        while (image_path := request.take_next_image()) is not None:
            processed_count: int = detected_count + len(unreadable_paths)
            self.batch_progressed.emit(processed_count, total_count)
            try:
                loaded_image: LoadedImage = LoadedImage.open(image_path)
            except Exception:
                unreadable_paths.append(image_path)
                continue
            self.status_changed.emit(f"Detecting {image_path.name} ({processed_count + 1}/{total_count}) ...")
            try:
                outcome: DetectionOutcome = self._session.detect(
                    DetectionRequest(
                        settings=request.settings,
                        image_path=image_path,
                        labeled_prompt=request.labeled_prompt,
                    ),
                    loaded_image.image,
                )
            except Exception as error:
                self.batch_failed.emit(f"{image_path.name}: {type(error).__name__}: {error}")
                return
            detected_count += 1
            self.image_detected.emit(image_path, outcome.result)
        is_cancelled: bool = detected_count + len(unreadable_paths) < total_count
        if not is_cancelled:
            self.batch_progressed.emit(total_count, total_count)
        self.batch_finished.emit(
            BatchDetectionSummary(
                detected_count=detected_count,
                unreadable_paths=tuple(unreadable_paths),
                is_cancelled=is_cancelled,
            )
        )
