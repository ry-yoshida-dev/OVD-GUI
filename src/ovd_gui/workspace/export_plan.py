from dataclasses import dataclass

from ..detection import DetectorProfile


@dataclass(frozen=True)
class ExportPlan:
    """
    What an export would write, shown before the user chooses its options.

    Attributes
    ----------
    profile : DetectorProfile
        Model whose results are exported: the shown one, or the one chosen in the model settings.
    image_count : int
        Open images.
    pending_count : int
        Open images without an up-to-date result of the model, detected before exporting.
    issue : str
        Why the export cannot start now; empty when it can.
    """

    profile: DetectorProfile
    image_count: int
    pending_count: int
    issue: str
