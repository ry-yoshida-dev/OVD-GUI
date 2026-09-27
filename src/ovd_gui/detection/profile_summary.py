from dataclasses import dataclass

from .detector_profile import DetectorProfile


@dataclass(frozen=True)
class ProfileSummary:
    """
    How many results are stored for one detector profile, and how many of them are outdated.

    Attributes
    ----------
    profile : DetectorProfile
        Model and options of the results.
    image_count : int
        Images detected with the profile.
    outdated_image_count : int
        Images among them detected with other classes, phrases or reference boxes than the current ones.
    detection_count : int
        Detections in those images.
    """

    profile: DetectorProfile
    image_count: int
    outdated_image_count: int
    detection_count: int
