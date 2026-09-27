from dataclasses import dataclass
from pathlib import Path

from .analysis_state import AnalysisState


@dataclass(frozen=True)
class ImageStatusRow:
    """
    Table row standing for an open image that has no detection to list.

    Attributes
    ----------
    image_path : Path
        Image the row stands for.
    state : AnalysisState
        Whether the image is undetected or was detected without result.
    """

    image_path: Path
    state: AnalysisState
