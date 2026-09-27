from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from ..detection import DetectionCatalog, DetectionRecord
from .box_matcher import BoxMatcher
from .class_comparison import ClassComparison


@dataclass(frozen=True)
class ProfileComparison:
    """
    Detections of two detector profiles compared class by class on the images both have detected.

    Every stored detection takes part, whether rejected or below a minimum confidence, so the comparison is about
    the models rather than the review.

    Attributes
    ----------
    image_count : int
        Images detected by both profiles.
    classes : tuple[ClassComparison, ...]
        One entry per current class, followed by the other classes either profile found, sorted by name.
    iou_threshold : float
        Smallest box overlap for a detection of one profile to pair with one of the other.
    """

    image_count: int
    classes: tuple[ClassComparison, ...]
    iou_threshold: float

    @classmethod
    def between(
        cls,
        baseline: DetectionCatalog,
        candidate: DetectionCatalog,
        image_paths: Sequence[Path],
        class_names: Sequence[str],
        matcher: BoxMatcher | None = None,
    ) -> "ProfileComparison":
        """
        Compare the results of two profiles.

        Parameters
        ----------
        baseline : DetectionCatalog
            Results of the shown profile.
        candidate : DetectionCatalog
            Results of the compared profile.
        image_paths : Sequence[Path]
            Images to compare, typically the open ones; images either profile has not detected are skipped.
        class_names : Sequence[str]
            Current classes, listed first and in this order.
        matcher : BoxMatcher | None, optional
            Pairing of the boxes of one class; ``None`` pairs boxes overlapping by at least half.

        Returns
        -------
        ProfileComparison
            Counts per class.
        """
        box_matcher: BoxMatcher = matcher or BoxMatcher()
        counts: dict[str, list[int]] = {class_name: [0, 0, 0] for class_name in class_names}
        compared_paths: list[Path] = [
            image_path
            for image_path in dict.fromkeys(image_paths)
            if image_path in baseline and image_path in candidate
        ]
        for image_path in compared_paths:
            baseline_records: tuple[DetectionRecord, ...] = baseline.records_of(image_path)
            candidate_records: tuple[DetectionRecord, ...] = candidate.records_of(image_path)
            found_names: dict[str, None] = dict.fromkeys(
                record.detection.class_name for record in (*baseline_records, *candidate_records)
            )
            for class_name in found_names:
                baseline_boxes: NDArray[np.float64] = cls._boxes_of(baseline_records, class_name)
                candidate_boxes: NDArray[np.float64] = cls._boxes_of(candidate_records, class_name)
                class_counts: list[int] = counts.setdefault(class_name, [0, 0, 0])
                class_counts[0] += len(baseline_boxes)
                class_counts[1] += len(candidate_boxes)
                class_counts[2] += len(box_matcher.pairs(baseline_boxes, candidate_boxes))
        other_names: list[str] = sorted((name for name in counts if name not in class_names), key=str.casefold)
        return cls(
            image_count=len(compared_paths),
            classes=tuple(
                ClassComparison(
                    class_name=class_name,
                    baseline_count=counts[class_name][0],
                    candidate_count=counts[class_name][1],
                    matched_count=counts[class_name][2],
                )
                for class_name in (*dict.fromkeys(class_names), *other_names)
            ),
            iou_threshold=box_matcher.iou_threshold,
        )

    @staticmethod
    def _boxes_of(records: Sequence[DetectionRecord], class_name: str) -> NDArray[np.float64]:
        return np.array(
            [record.xyxy for record in records if record.detection.class_name == class_name], dtype=np.float64
        ).reshape(-1, 4)
