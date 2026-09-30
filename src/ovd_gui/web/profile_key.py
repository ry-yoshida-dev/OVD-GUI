from collections.abc import Iterable

from ..detection import DetectorProfile


class ProfileKey:
    """
    Text naming a detector profile in the browser, stable for as long as the profile is stored.
    """

    SEPARATOR = "|"

    @classmethod
    def of(cls, profile: DetectorProfile) -> str:
        """
        Key of a profile.

        Parameters
        ----------
        profile : DetectorProfile
            Profile to name.

        Returns
        -------
        str
            Backend, weights, device, precision and thresholds joined by ``|``.
        """
        return cls.SEPARATOR.join(
            (
                profile.backend.value,
                profile.weights_path,
                profile.device.value,
                profile.precision_text,
                repr(profile.thresholds.confidence_threshold),
                repr(profile.thresholds.nms_iou_threshold),
            )
        )

    @classmethod
    def find(cls, key: str, profiles: Iterable[DetectorProfile]) -> DetectorProfile:
        """
        Profile named by a key.

        Parameters
        ----------
        key : str
            Key made by ``of``.
        profiles : Iterable[DetectorProfile]
            Stored profiles.

        Returns
        -------
        DetectorProfile
            Profile whose key is ``key``.

        Raises
        ------
        KeyError
            If no stored profile has the key.
        """
        for profile in profiles:
            if cls.of(profile) == key:
                return profile
        raise KeyError(f"No stored results of the model {key!r}.")
