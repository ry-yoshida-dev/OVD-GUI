from dataclasses import dataclass

from .detector_profile import DetectorProfile


@dataclass(frozen=True)
class ProfileSummary:
    """
    How many results are stored for one detector profile.

    Attributes
    ----------
    profile : DetectorProfile
        Model and options of the results.
    image_count : int
        Images detected with the profile.
    detection_count : int
        Detections in those images.
    """

    profile: DetectorProfile
    image_count: int
    detection_count: int
