from dataclasses import dataclass


@dataclass(frozen=True)
class RangeCondition:
    """
    Condition of a numeric column listing only rows whose value lies within bounds.

    Rows without a value, such as images without detections, never pass.

    Attributes
    ----------
    minimum : float | None
        Lowest accepted value; ``None`` leaves the range open below.
    maximum : float | None
        Highest accepted value; ``None`` leaves the range open above.

    Raises
    ------
    ValueError
        If both bounds are open or ``minimum`` exceeds ``maximum``.
    """

    minimum: float | None
    maximum: float | None

    def __post_init__(self) -> None:
        if self.minimum is None and self.maximum is None:
            raise ValueError("at least one of minimum and maximum must be given")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError(f"minimum must not exceed maximum. got {self.minimum} > {self.maximum}")

    def accepts(self, value: float | None) -> bool:
        """
        Whether a cell passes the condition.

        Parameters
        ----------
        value : float | None
            Number shown in the cell, or ``None`` for a blank cell.

        Returns
        -------
        bool
            True if ``value`` lies within the bounds.
        """
        if value is None:
            return False
        if self.minimum is not None and value < self.minimum:
            return False
        return self.maximum is None or value <= self.maximum

    @property
    def description(self) -> str:
        """
        Short summary of the bounds.

        Returns
        -------
        str
            Bounds written as an inequality.
        """
        if self.maximum is None:
            return f"≥ {self.minimum:g}"
        if self.minimum is None:
            return f"≤ {self.maximum:g}"
        return f"{self.minimum:g} – {self.maximum:g}"
