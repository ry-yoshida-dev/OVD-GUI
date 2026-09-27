from dataclasses import dataclass

from open_vocabulary_detector import DetectionResult

from .detection_request import DetectionRequest


@dataclass(frozen=True, eq=False)
class DetectionOutcome:
    """
    Result of a detection run together with how it was obtained.

    Attributes
    ----------
    request : DetectionRequest
        Request the result answers.
    result : DetectionResult
        Detections in the request image.
    inference_seconds : float
        Wall-clock time of the forward pass and post-processing.
    is_model_reloaded : bool
        Whether the model had to be (re)loaded for this run.
    """

    request: DetectionRequest
    result: DetectionResult
    inference_seconds: float
    is_model_reloaded: bool
