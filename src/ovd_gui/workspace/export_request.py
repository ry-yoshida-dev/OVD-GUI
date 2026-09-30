from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ..export import ExportOptions


@dataclass(frozen=True)
class ExportRequest:
    """
    Export asked for by the user.

    Attributes
    ----------
    options : ExportOptions
        Format, output directory and which detections are exported.
    listed_indices : Mapping[Path, frozenset[int]] | None
        Detections listed in the detection table per image, used when only listed detections are exported; ``None``
        when the table lists every detection.
    is_confidence_shown : bool
        Whether the images saved with boxes label each box with its confidence.
    """

    options: ExportOptions
    listed_indices: Mapping[Path, frozenset[int]] | None
    is_confidence_shown: bool
