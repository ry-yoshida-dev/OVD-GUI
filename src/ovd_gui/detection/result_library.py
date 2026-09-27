from pathlib import Path

from open_vocabulary_detector import DetectionResult

from .detection_catalog import DetectionCatalog
from .detection_record import DetectionRecord
from .detector_profile import DetectorProfile
from .labeled_prompt import LabeledPrompt
from .profile_summary import ProfileSummary
from .prompt_change import PromptChange
from .prompt_signature import PromptSignature


class ResultLibrary:
    """
    Latest result of every image, kept separately for every detector profile.

    Detecting with another model or other thresholds adds a profile instead of replacing earlier results, so the
    results of several models can be compared without detecting again. Editing the classes keeps every result; the
    images detected with other classes are reported as outdated instead. Profiles keep the order in which they were
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
        self, profile: DetectorProfile, image_path: Path, result: DetectionResult, labeled_prompt: LabeledPrompt
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
        labeled_prompt : LabeledPrompt
            Prompt the result was detected with.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Detections of the image in result order.

        Raises
        ------
        ValueError
            If the prompt does not have as many queries as the prompt of the result.
        """
        return self.add(profile).record(image_path, result, labeled_prompt)

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

    def outdated_images(self, profile: DetectorProfile, current: PromptSignature) -> dict[Path, PromptChange]:
        """
        Images of one profile detected with another prompt than the current one.

        Parameters
        ----------
        profile : DetectorProfile
            Stored profile.
        current : PromptSignature
            Phrases and reference boxes of the current classes, whatever the model; reference boxes are ignored for
            a model without image prompts.

        Returns
        -------
        dict[Path, PromptChange]
            Change of every outdated image, in recording order.

        Raises
        ------
        KeyError
            If the profile is not stored.
        """
        return self.catalog_of(profile).outdated_images(
            current.for_prompt_kinds(profile.backend.supported_prompt_kinds)
        )

    def prompt_change_of(
        self, profile: DetectorProfile, image_path: Path, current: PromptSignature
    ) -> PromptChange | None:
        """
        How the classes have changed since one image was detected with one profile.

        Parameters
        ----------
        profile : DetectorProfile
            Profile to look up.
        image_path : Path
            Image to look up.
        current : PromptSignature
            Phrases and reference boxes of the current classes, whatever the model.

        Returns
        -------
        PromptChange | None
            ``None`` if the image has not been detected with the profile.
        """
        catalog: DetectionCatalog | None = self._catalogs.get(profile)
        if catalog is None:
            return None
        return catalog.prompt_change_of(image_path, current.for_prompt_kinds(profile.backend.supported_prompt_kinds))

    def summaries(self, current: PromptSignature) -> tuple[ProfileSummary, ...]:
        """
        Image, outdated image and detection counts of every profile.

        Parameters
        ----------
        current : PromptSignature
            Phrases and reference boxes of the current classes, whatever the model.

        Returns
        -------
        tuple[ProfileSummary, ...]
            One summary per profile, in the order the profiles were added.
        """
        return tuple(
            ProfileSummary(
                profile=profile,
                image_count=len(catalog),
                outdated_image_count=len(self.outdated_images(profile, current)),
                detection_count=len(catalog.records()),
            )
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
