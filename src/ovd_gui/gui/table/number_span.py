from dataclasses import dataclass


@dataclass(frozen=True)
class NumberSpan:
    """
    Smallest and largest value found in a numeric column.

    Attributes
    ----------
    smallest : float
        Lowest value.
    largest : float
        Highest value.
    """

    smallest: float
    largest: float
