from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BatchDetectionSummary:
    """
    How a batch detection ended.

    Attributes
    ----------
    detected_count : int
        Images whose detection finished.
    unreadable_paths : tuple[Path, ...]
        Image files that could not be opened and were skipped.
    is_cancelled : bool
        Whether the batch stopped early on request.
    """

    detected_count: int
    unreadable_paths: tuple[Path, ...]
    is_cancelled: bool
