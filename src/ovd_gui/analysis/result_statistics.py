from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ..detection import DetectionCatalog, DetectionRecord
from ..review import ClassThresholds
from .class_statistics import ClassStatistics


@dataclass(frozen=True)
class ResultStatistics:
    """
    Per-class statistics of the results of one detector profile over the open images.

    Attributes
    ----------
    image_count : int
        Images the statistics cover.
    detected_image_count : int
        Images among them with a stored result.
    classes : tuple[ClassStatistics, ...]
        One entry per current class, even without detections, followed by the classes found only in results
        detected with other classes, sorted by name.
    """

    image_count: int
    detected_image_count: int
    classes: tuple[ClassStatistics, ...]

    @classmethod
    def of(
        cls,
        catalog: DetectionCatalog,
        image_paths: Sequence[Path],
        class_names: Sequence[str],
        thresholds: ClassThresholds,
    ) -> "ResultStatistics":
        """
        Gather the statistics of some images.

        Parameters
        ----------
        catalog : DetectionCatalog
            Results of one profile.
        image_paths : Sequence[Path]
            Images to cover, typically the open ones; images without a result count as not detected.
        class_names : Sequence[str]
            Current classes, listed first and in this order.
        thresholds : ClassThresholds
            Minimum confidence of each class.

        Returns
        -------
        ResultStatistics
            Counts and confidences per class.
        """
        records_by_class: dict[str, list[DetectionRecord]] = {class_name: [] for class_name in class_names}
        detected_image_count: int = 0
        for image_path in dict.fromkeys(image_paths):
            if image_path not in catalog:
                continue
            detected_image_count += 1
            for record in catalog.records_of(image_path):
                records_by_class.setdefault(record.detection.class_name, []).append(record)
        other_names: list[str] = sorted(
            (class_name for class_name in records_by_class if class_name not in class_names), key=str.casefold
        )
        return cls(
            image_count=len(dict.fromkeys(image_paths)),
            detected_image_count=detected_image_count,
            classes=tuple(
                cls._class_statistics(class_name, records_by_class[class_name], catalog, thresholds)
                for class_name in (*dict.fromkeys(class_names), *other_names)
            ),
        )

    def class_named(self, class_name: str) -> ClassStatistics | None:
        """
        Statistics of one class.

        Parameters
        ----------
        class_name : str
            Class to look up.

        Returns
        -------
        ClassStatistics | None
            ``None`` when the class is neither current nor found in the results.
        """
        return next((entry for entry in self.classes if entry.class_name == class_name), None)

    @property
    def confidences(self) -> tuple[float, ...]:
        """
        Confidence of every detection of every class.

        Returns
        -------
        tuple[float, ...]
            Confidences in ascending order.
        """
        return tuple(sorted(confidence for entry in self.classes for confidence in entry.confidences))

    @staticmethod
    def _class_statistics(
        class_name: str, records: Sequence[DetectionRecord], catalog: DetectionCatalog, thresholds: ClassThresholds
    ) -> ClassStatistics:
        accepted_records: list[DetectionRecord] = [record for record in records if catalog.is_accepted(record)]
        return ClassStatistics(
            class_name=class_name,
            image_count=len({record.image_path for record in records}),
            detection_count=len(records),
            rejected_count=len(records) - len(accepted_records),
            below_minimum_count=sum(
                1 for record in accepted_records if not thresholds.accepts(class_name, record.detection.confidence)
            ),
            confidences=tuple(sorted(record.detection.confidence for record in records)),
        )
