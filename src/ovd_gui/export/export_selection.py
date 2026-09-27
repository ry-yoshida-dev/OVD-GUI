from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from open_vocabulary_detector import DetectionResult

from ..detection import DetectionCatalog, DetectionRecord
from ..review import ClassThresholds


@dataclass(frozen=True)
class ExportSelection:
    """
    Which stored detections of an image are exported.

    A detection is exported when it is not rejected, reaches the minimum confidence of its class and the export's
    own minimum, and, when the export is limited to the table, is listed there.

    Attributes
    ----------
    class_thresholds : ClassThresholds
        Minimum confidence of each class.
    minimum_confidence : float
        Minimum confidence of every detection, in ``[0, 1]``.
    listed_indices : Mapping[Path, frozenset[int]] | None
        Detections listed in the table per image; ``None`` does not limit the export to the table.

    Raises
    ------
    ValueError
        If ``minimum_confidence`` is outside ``[0, 1]``.
    """

    class_thresholds: ClassThresholds
    minimum_confidence: float = 0.0
    listed_indices: Mapping[Path, frozenset[int]] | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError(f"minimum_confidence must be in [0, 1]. got {self.minimum_confidence}")

    def is_selected(self, record: DetectionRecord, catalog: DetectionCatalog) -> bool:
        """
        Whether one detection is exported.

        Parameters
        ----------
        record : DetectionRecord
            Stored detection.
        catalog : DetectionCatalog
            Results holding ``record``, telling whether it is rejected.

        Returns
        -------
        bool
            True when every condition holds.
        """
        confidence: float = record.detection.confidence
        is_listed: bool = self.listed_indices is None or record.detection_index in self.listed_indices.get(
            record.image_path, frozenset()
        )
        return (
            is_listed
            and catalog.is_accepted(record)
            and confidence >= self.minimum_confidence
            and self.class_thresholds.accepts(record.detection.class_name, confidence)
        )

    def selected_result(self, catalog: DetectionCatalog, image_path: Path) -> DetectionResult | None:
        """
        Exported detections of one image.

        Parameters
        ----------
        catalog : DetectionCatalog
            Results of the exported model.
        image_path : Path
            Image to export.

        Returns
        -------
        DetectionResult | None
            The stored result narrowed to the exported detections, possibly empty; ``None`` if the image has not
            been detected.
        """
        result: DetectionResult | None = catalog.result_of(image_path)
        if result is None:
            return None
        selected_indices: list[int] = [
            record.detection_index for record in catalog.records_of(image_path) if self.is_selected(record, catalog)
        ]
        return result.select(np.array(selected_indices, dtype=np.int64))
