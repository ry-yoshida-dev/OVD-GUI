from dataclasses import dataclass

from .detection_failure_kind import DetectionFailureKind


@dataclass(frozen=True)
class DetectionFailure:
    """
    Why a single detection failed, with a message for the user.

    Attributes
    ----------
    kind : DetectionFailureKind
        Whether the image file could not be read or the model failed to load or detect.
    message : str
        Error type and message.
    """

    kind: DetectionFailureKind
    message: str

    @classmethod
    def of(cls, kind: DetectionFailureKind, error: BaseException) -> "DetectionFailure":
        """
        Describe an error raised while detecting.

        Parameters
        ----------
        kind : DetectionFailureKind
            Stage the error was raised in.
        error : BaseException
            Raised error.

        Returns
        -------
        DetectionFailure
            Failure naming the error type and message.
        """
        return cls(kind=kind, message=f"{type(error).__name__}: {error}")
