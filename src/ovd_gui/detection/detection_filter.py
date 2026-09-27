from dataclasses import dataclass, field
from pathlib import Path

from .detection_record import DetectionRecord


@dataclass(frozen=True)
class DetectionFilter:
    """
    Conditions a detection must meet to be listed.

    Attributes
    ----------
    class_names : frozenset[str], optional
        Only detections of these classes; empty accepts every class.
    image_name_text : str, optional
        Case-insensitive text the image file name must contain; blank accepts every name.
    minimum_confidence : float, optional
        Lowest accepted confidence, in ``[0, 1]``.

    Raises
    ------
    ValueError
        If ``minimum_confidence`` lies outside ``[0, 1]``.
    """

    class_names: frozenset[str] = field(default_factory=frozenset[str])
    image_name_text: str = ""
    minimum_confidence: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError(f"minimum_confidence must be in [0, 1]. got {self.minimum_confidence}")

    def accepts(self, record: DetectionRecord) -> bool:
        """
        Whether a detection meets every condition.

        Parameters
        ----------
        record : DetectionRecord
            Detection to test.

        Returns
        -------
        bool
            True if the detection is listed.
        """
        if self.class_names and record.detection.class_name not in self.class_names:
            return False
        if record.detection.confidence < self.minimum_confidence:
            return False
        return self._accepts_image_name(record.image_path)

    def accepts_image_without_detections(self, image_path: Path) -> bool:
        """
        Whether an image with no detection to list, undetected or detected empty, is listed.

        Such an image is listed only while every class is accepted, since it has no detection of any class.

        Parameters
        ----------
        image_path : Path
            Image to test.

        Returns
        -------
        bool
            True if the image is listed.
        """
        return not self.class_names and self._accepts_image_name(image_path)

    def _accepts_image_name(self, image_path: Path) -> bool:
        return self.image_name_text.strip().casefold() in image_path.name.casefold()
