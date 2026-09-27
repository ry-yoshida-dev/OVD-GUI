from dataclasses import dataclass, field
from pathlib import Path
from threading import Event

from open_vocabulary_detector import DetectorSettings

from .image_queue import ImageQueue
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
        Image files, detected in this order unless one is prioritized.
    cancellation : Event, optional
        Set from any thread to stop before the next image.
    waiting_images : ImageQueue
        Images not yet taken by the worker; built from ``image_paths``.

    Raises
    ------
    ValueError
        If no image path is given.
    """

    settings: DetectorSettings
    labeled_prompt: LabeledPrompt
    image_paths: tuple[Path, ...]
    cancellation: Event = field(default_factory=Event)
    waiting_images: ImageQueue = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.image_paths:
            raise ValueError("image_paths must not be empty")
        object.__setattr__(self, "waiting_images", ImageQueue(self.image_paths))

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

    def take_next_image(self) -> Path | None:
        """
        Remove the image to detect next.

        Returns
        -------
        Path | None
            Next image, or ``None`` when every image was taken or cancellation was requested.
        """
        return None if self.is_cancelled else self.waiting_images.take()

    def prioritize(self, image_path: Path) -> bool:
        """
        Detect a waiting image before the others; safe to call from any thread.

        Parameters
        ----------
        image_path : Path
            Image to detect next.

        Returns
        -------
        bool
            True when the image was still waiting.
        """
        return self.waiting_images.prioritize(image_path)
