from dataclasses import dataclass


@dataclass(frozen=True)
class ClassComparison:
    """
    Detections of one class found by two models on the same images.

    Attributes
    ----------
    class_name : str
        Compared class.
    baseline_count : int
        Detections of the class by the shown model.
    candidate_count : int
        Detections of the class by the compared model.
    matched_count : int
        Detections of the shown model paired with one of the compared model, one to one, by box overlap.
    """

    class_name: str
    baseline_count: int
    candidate_count: int
    matched_count: int

    @property
    def baseline_only_count(self) -> int:
        """
        Detections only the shown model found.

        Returns
        -------
        int
            Unpaired detections of the shown model.
        """
        return self.baseline_count - self.matched_count

    @property
    def candidate_only_count(self) -> int:
        """
        Detections only the compared model found.

        Returns
        -------
        int
            Unpaired detections of the compared model.
        """
        return self.candidate_count - self.matched_count
