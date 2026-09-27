import statistics
from dataclasses import dataclass

from .confidence_histogram import ConfidenceHistogram


@dataclass(frozen=True)
class ClassStatistics:
    """
    Detections of one class over a set of images.

    Attributes
    ----------
    class_name : str
        Class of the detections.
    image_count : int
        Images with at least one detection of the class.
    detection_count : int
        Detections of the class.
    rejected_count : int
        Detections unchecked in the detection table.
    below_minimum_count : int
        Checked detections below the minimum confidence of the class.
    confidences : tuple[float, ...]
        Confidence of every detection, rejected or not, in ascending order.
    """

    class_name: str
    image_count: int
    detection_count: int
    rejected_count: int
    below_minimum_count: int
    confidences: tuple[float, ...]

    @property
    def kept_count(self) -> int:
        """
        Detections shown and exported.

        Returns
        -------
        int
            Detections that are neither rejected nor below the minimum confidence.
        """
        return self.detection_count - self.rejected_count - self.below_minimum_count

    @property
    def mean_confidence(self) -> float | None:
        """
        Mean confidence of the class.

        Returns
        -------
        float | None
            ``None`` without detections.
        """
        return statistics.fmean(self.confidences) if self.confidences else None

    @property
    def median_confidence(self) -> float | None:
        """
        Median confidence of the class.

        Returns
        -------
        float | None
            ``None`` without detections.
        """
        return statistics.median(self.confidences) if self.confidences else None

    def histogram(self, bin_count: int = ConfidenceHistogram.DEFAULT_BIN_COUNT) -> ConfidenceHistogram:
        """
        Confidences of the class per bin.

        Parameters
        ----------
        bin_count : int, optional
            Number of bins over ``[0, 1]``.

        Returns
        -------
        ConfidenceHistogram
            Counts of every detection of the class.
        """
        return ConfidenceHistogram.of(self.confidences, bin_count)
