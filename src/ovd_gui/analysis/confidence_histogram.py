from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceHistogram:
    """
    How many detections fall in each equal-width confidence bin over ``[0, 1]``.

    Attributes
    ----------
    bin_counts : tuple[int, ...]
        Detections per bin, from the lowest confidences to the highest; a confidence of exactly 1 is counted in the
        last bin.

    Raises
    ------
    ValueError
        If there is no bin or a count is negative.
    """

    DEFAULT_BIN_COUNT = 20

    bin_counts: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.bin_counts:
            raise ValueError("a histogram needs at least one bin")
        if any(count < 0 for count in self.bin_counts):
            raise ValueError(f"bin counts must not be negative. got {self.bin_counts}")

    @classmethod
    def of(cls, confidences: Iterable[float], bin_count: int = DEFAULT_BIN_COUNT) -> "ConfidenceHistogram":
        """
        Count confidences per bin.

        Parameters
        ----------
        confidences : Iterable[float]
            Confidences in ``[0, 1]``.
        bin_count : int, optional
            Number of bins.

        Returns
        -------
        ConfidenceHistogram
            Counts of ``bin_count`` bins.

        Raises
        ------
        ValueError
            If ``bin_count`` is not positive or a confidence is outside ``[0, 1]``.
        """
        if bin_count <= 0:
            raise ValueError(f"bin_count must be positive. got {bin_count}")
        counts: list[int] = [0] * bin_count
        for confidence in confidences:
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"confidences must be in [0, 1]. got {confidence}")
            counts[min(int(confidence * bin_count), bin_count - 1)] += 1
        return cls(tuple(counts))

    @property
    def bin_width(self) -> float:
        """
        Confidence span of one bin.

        Returns
        -------
        float
            ``1 / len(bin_counts)``.
        """
        return 1.0 / len(self.bin_counts)

    @property
    def largest_count(self) -> int:
        """
        Count of the fullest bin.

        Returns
        -------
        int
            0 for a histogram without detections.
        """
        return max(self.bin_counts)

    @property
    def total_count(self) -> int:
        """
        Detections over every bin.

        Returns
        -------
        int
            Sum of the bin counts.
        """
        return sum(self.bin_counts)
