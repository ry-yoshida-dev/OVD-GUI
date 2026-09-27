from dataclasses import dataclass

from open_vocabulary_detector import DetectionResult


@dataclass(frozen=True, eq=False)
class DetectionOverlay:
    """
    Detections to draw over the shown image.

    Attributes
    ----------
    result : DetectionResult
        Result of the shown model for the image.
    listed_indices : frozenset[int]
        Detections of ``result`` listed in the detection table, i.e. passing its filters and the class minimums;
        the others are not drawn.
    rejected_indices : frozenset[int]
        Detections of ``result`` rejected for export.
    comparison : DetectionResult | None
        Result of the compared model for the same image, drawn dotted; ``None`` without comparison.
    comparison_name : str
        Name of the compared model, prefixed to its labels.
    """

    result: DetectionResult
    listed_indices: frozenset[int]
    rejected_indices: frozenset[int]
    comparison: DetectionResult | None = None
    comparison_name: str = ""
