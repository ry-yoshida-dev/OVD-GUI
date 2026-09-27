from dataclasses import dataclass, field
from pathlib import Path
from threading import Event

from open_vocabulary_detector import DetectorSettings

from .labeled_prompt import LabeledPrompt


@dataclass(frozen=True, eq=False)
class BatchDetectionRequest:
    """
    Detection of the same prompt in several image files.

    Attributes
    ----------
    settings : DetectorSettings
        Model and thresholds to detect with.
    labeled_prompt : LabeledPrompt
        Classes to detect with their queries, and the label of each query.
    image_paths : tuple[Path, ...]
        Image files, detected in this order.
    cancellation : Event, optional
        Set from any thread to stop before the next image.

    Raises
    ------
    ValueError
        If no image path is given.
    """

    settings: DetectorSettings
    labeled_prompt: LabeledPrompt
    image_paths: tuple[Path, ...]
    cancellation: Event = field(default_factory=Event)

    def __post_init__(self) -> None:
        if not self.image_paths:
            raise ValueError("image_paths must not be empty")

    @property
    def is_cancelled(self) -> bool:
        """
        Whether cancellation was requested.

        Returns
        -------
        bool
            True once ``cancel`` has been called.
        """
        return self.cancellation.is_set()

    def cancel(self) -> None:
        """
        Request the batch to stop before its next image.
        """
        self.cancellation.set()
