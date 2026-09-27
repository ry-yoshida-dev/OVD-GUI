from enum import Enum


class DetectionFailureKind(Enum):
    """
    Why a single detection produced no result.
    """

    UNREADABLE_IMAGE = "unreadable_image"
    DETECTION_ERROR = "detection_error"
