from dataclasses import dataclass
from pathlib import Path

from open_vocabulary_detector import Detection


@dataclass(frozen=True)
class DetectionRecord:
    """
    One detection located in the image it was found in.

    Attributes
    ----------
    image_path : Path
        Image file the detection belongs to.
    detection_index : int
        Position of the detection in the result of its image.
    detection : Detection
        Box, confidence, class and matched query of the detection.
    query_label : str
        Label of the matched query: its phrase, or the reference image name of a visual query.
    """

    image_path: Path
    detection_index: int
    detection: Detection
    query_label: str

    @property
    def xyxy(self) -> tuple[float, float, float, float]:
        """
        Corners of the box.

        Returns
        -------
        tuple[float, float, float, float]
            ``(x1, y1, x2, y2)`` in image pixels.
        """
        x_min, y_min, x_max, y_max = (float(value) for value in self.detection.box.value.tolist())
        return (x_min, y_min, x_max, y_max)
