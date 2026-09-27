from dataclasses import dataclass
from pathlib import Path

from .detection_record import DetectionRecord


@dataclass(frozen=True)
class DetectionFilter:
    """
    Conditions a detection must meet to be listed.

    Attributes
    ----------
    image_path : Path | None, optional
        Only detections of this image; ``None`` accepts every image.
    class_name : str | None, optional
        Only detections of this class; ``None`` accepts every class.
    image_name_text : str, optional
        Case-insensitive text the image file name must contain; blank accepts every name.
    minimum_confidence : float, optional
        Lowest accepted confidence, in ``[0, 1]``.

    Raises
    ------
    ValueError
        If ``minimum_confidence`` lies outside ``[0, 1]``.
    """

    image_path: Path | None = None
    class_name: str | None = None
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
        if self.image_path is not None and record.image_path != self.image_path:
            return False
        if self.class_name is not None and record.detection.class_name != self.class_name:
            return False
        if record.detection.confidence < self.minimum_confidence:
            return False
        searched_text: str = self.image_name_text.strip().casefold()
        return searched_text in record.image_path.name.casefold()
