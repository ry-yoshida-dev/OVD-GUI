from pathlib import Path

from open_vocabulary_detector import DetectionResult

from .detection_catalog import DetectionCatalog
from .detection_record import DetectionRecord
from .detector_profile import DetectorProfile
from .profile_summary import ProfileSummary


class ResultLibrary:
    """
    Latest result of every image, kept separately for every detector profile.

    Detecting with another model or other thresholds adds a profile instead of replacing earlier results, so the
    results of several models can be compared without detecting again. Profiles keep the order in which they were
    added; results are kept in memory for the session only.
    """

    def __init__(self) -> None:
        self._catalogs: dict[DetectorProfile, DetectionCatalog] = {}

    def __contains__(self, profile: object) -> bool:
        return profile in self._catalogs

    @property
    def profiles(self) -> tuple[DetectorProfile, ...]:
        """
        Stored profiles.

        Returns
        -------
        tuple[DetectorProfile, ...]
            Profiles in the order they were added.
        """
        return tuple(self._catalogs)

    def add(self, profile: DetectorProfile) -> DetectionCatalog:
        """
        Make sure a profile is stored, without results yet if it is new.

        Parameters
        ----------
        profile : DetectorProfile
            Profile to store.

        Returns
        -------
        DetectionCatalog
            Results of the profile.
        """
        return self._catalogs.setdefault(profile, DetectionCatalog())

    def record(
        self, profile: DetectorProfile, image_path: Path, result: DetectionResult, query_labels: tuple[str, ...]
    ) -> tuple[DetectionRecord, ...]:
        """
        Store the result of one image under its profile, replacing an earlier result of the same profile.

        Parameters
        ----------
        profile : DetectorProfile
            Model and options the result was detected with; added if not stored yet.
        image_path : Path
            Image file the result was detected in.
        result : DetectionResult
            Detections of the image.
        query_labels : tuple[str, ...]
            Label of each query of the prompt the result was detected with.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Detections of the image in result order.

        Raises
        ------
        ValueError
            If there is not exactly one label per prompt query.
        """
        return self.add(profile).record(image_path, result, query_labels)

    def catalog_of(self, profile: DetectorProfile) -> DetectionCatalog:
        """
        Results of one profile.

        Parameters
        ----------
        profile : DetectorProfile
            Stored profile.

        Returns
        -------
        DetectionCatalog
            Latest result of every image detected with the profile.

        Raises
        ------
        KeyError
            If the profile is not stored.
        """
        if profile not in self._catalogs:
            raise KeyError(f"no results stored for {profile.model_name} ({profile.options_text})")
        return self._catalogs[profile]

    def summaries(self) -> tuple[ProfileSummary, ...]:
        """
        Image and detection counts of every profile.

        Returns
        -------
        tuple[ProfileSummary, ...]
            One summary per profile, in the order the profiles were added.
        """
        return tuple(
            ProfileSummary(profile=profile, image_count=len(catalog), detection_count=len(catalog.records()))
            for profile, catalog in self._catalogs.items()
        )

    def remove(self, profile: DetectorProfile) -> None:
        """
        Forget the results of one profile.

        Parameters
        ----------
        profile : DetectorProfile
            Profile to forget; nothing happens if it is not stored.
        """
        self._catalogs.pop(profile, None)

    def clear(self) -> None:
        """
        Forget every profile and its results.
        """
        self._catalogs.clear()
