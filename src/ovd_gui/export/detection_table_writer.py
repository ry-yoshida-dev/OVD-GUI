import csv
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from ..detection import DetectionCatalog, DetectionRecord


class DetectionTableWriter:
    """
    Detections written as a CSV table, one detection per row, in the given order.

    Columns are the image file, class, matched prompt, confidence, box corners in pixels of the EXIF-upright image,
    and whether the detection is kept (``true``) or rejected (``false``). The file is UTF-8 with a header row.
    """

    HEADER: ClassVar[tuple[str, ...]] = ("image", "class", "prompt", "confidence", "x1", "y1", "x2", "y2", "kept")

    def write(self, records: Sequence[DetectionRecord], catalog: DetectionCatalog, path: Path) -> None:
        """
        Write detections to a CSV file, replacing it.

        Parameters
        ----------
        records : Sequence[DetectionRecord]
            Detections in row order.
        catalog : DetectionCatalog
            Results holding ``records``, telling whether each is rejected.
        path : Path
            CSV file to write.

        Raises
        ------
        OSError
            If the file cannot be written.
        """
        rows: list[tuple[str | float, ...]] = [self.HEADER]
        for record in records:
            x_min, y_min, x_max, y_max = record.xyxy
            rows.append(
                (
                    str(record.image_path),
                    record.detection.class_name,
                    record.query_label,
                    float(record.detection.confidence),
                    x_min,
                    y_min,
                    x_max,
                    y_max,
                    "true" if catalog.is_accepted(record) else "false",
                )
            )
        with path.open("w", encoding="utf-8", newline="") as table_file:
            csv.writer(table_file).writerows(rows)
