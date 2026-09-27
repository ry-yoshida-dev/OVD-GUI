from collections.abc import Mapping
from types import MappingProxyType


class ClassThresholds:
    """
    Minimum confidence a detection needs to be kept, set per class on top of the detector's own threshold.

    Detections below the minimum of their class stay stored but are hidden from the detection table and the image,
    and left out of exports, so the cut can be tuned per class without detecting again. A class without its own
    minimum uses the default one. Minimums are keyed by class name, so they survive reordering the classes.
    """

    def __init__(self, default_minimum: float = 0.0, class_minimums: Mapping[str, float] | None = None) -> None:
        """
        Parameters
        ----------
        default_minimum : float, optional
            Minimum of every class without its own, in ``[0, 1]``.
        class_minimums : Mapping[str, float] | None, optional
            Own minimum of some classes, in ``[0, 1]``; ``None`` sets none.

        Raises
        ------
        ValueError
            If a minimum is outside ``[0, 1]`` or a class name is blank.
        """
        minimums: dict[str, float] = dict(class_minimums or {})
        for class_name, minimum in (("default", default_minimum), *minimums.items()):
            if not 0.0 <= minimum <= 1.0:
                raise ValueError(f"minimum confidence of {class_name} must be in [0, 1]. got {minimum}")
        if any(not class_name.strip() for class_name in minimums):
            raise ValueError(f"class names must not be blank. got {list(minimums)}")
        self._default_minimum: float = default_minimum
        self._class_minimums: MappingProxyType[str, float] = MappingProxyType(minimums)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ClassThresholds)
            and self._default_minimum == other._default_minimum
            and dict(self._class_minimums) == dict(other._class_minimums)
        )

    def __hash__(self) -> int:
        return hash((self._default_minimum, frozenset(self._class_minimums.items())))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(default_minimum={self._default_minimum}, {dict(self._class_minimums)})"

    @property
    def default_minimum(self) -> float:
        """
        Minimum of every class without its own.

        Returns
        -------
        float
            Confidence in ``[0, 1]``; 0 keeps every detection.
        """
        return self._default_minimum

    @property
    def class_minimums(self) -> Mapping[str, float]:
        """
        Classes with their own minimum.

        Returns
        -------
        Mapping[str, float]
            Read-only view of the minimum of each such class.
        """
        return self._class_minimums

    @property
    def is_effective(self) -> bool:
        """
        Whether any detection can be hidden.

        Returns
        -------
        bool
            True when the default or a class minimum is above 0.
        """
        return self._default_minimum > 0.0 or any(minimum > 0.0 for minimum in self._class_minimums.values())

    def minimum_of(self, class_name: str) -> float:
        """
        Minimum confidence of one class.

        Parameters
        ----------
        class_name : str
            Class to look up.

        Returns
        -------
        float
            Its own minimum, or the default one.
        """
        return self._class_minimums.get(class_name, self._default_minimum)

    def has_own_minimum(self, class_name: str) -> bool:
        """
        Whether a class overrides the default minimum.

        Parameters
        ----------
        class_name : str
            Class to look up.

        Returns
        -------
        bool
            True when the class has its own minimum.
        """
        return class_name in self._class_minimums

    def accepts(self, class_name: str, confidence: float) -> bool:
        """
        Whether a detection reaches the minimum of its class.

        Parameters
        ----------
        class_name : str
            Class of the detection.
        confidence : float
            Confidence of the detection.

        Returns
        -------
        bool
            True when ``confidence`` is at least the minimum of ``class_name``.
        """
        return confidence >= self.minimum_of(class_name)

    def with_default_minimum(self, default_minimum: float) -> "ClassThresholds":
        """
        Copy with another default minimum.

        Parameters
        ----------
        default_minimum : float
            New default minimum in ``[0, 1]``.

        Returns
        -------
        ClassThresholds
            Updated thresholds.

        Raises
        ------
        ValueError
            If ``default_minimum`` is outside ``[0, 1]``.
        """
        return ClassThresholds(default_minimum, self._class_minimums)

    def with_class_minimum(self, class_name: str, minimum: float | None) -> "ClassThresholds":
        """
        Copy with the own minimum of one class set or removed.

        Parameters
        ----------
        class_name : str
            Class to change.
        minimum : float | None
            New minimum in ``[0, 1]``; ``None`` makes the class use the default minimum.

        Returns
        -------
        ClassThresholds
            Updated thresholds.

        Raises
        ------
        ValueError
            If ``minimum`` is outside ``[0, 1]`` or ``class_name`` is blank.
        """
        minimums: dict[str, float] = dict(self._class_minimums)
        if minimum is None:
            minimums.pop(class_name, None)
        else:
            minimums[class_name] = minimum
        return ClassThresholds(self._default_minimum, minimums)
