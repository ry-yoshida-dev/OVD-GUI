from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt

from ...detection import DetectionRecord
from ..class_palette import ClassPalette
from .result_column import ResultColumn


class DetectionRecordModel(QAbstractTableModel):
    """
    Detections of every detected image, one per row.

    Rows of one image stay contiguous in the order of its result; replacing an image moves its rows to the end.
    ``SORT_ROLE`` gives raw values so that numbers sort numerically and image names case-insensitively.
    """

    SORT_ROLE: int = Qt.ItemDataRole.UserRole.value
    ROOT_INDEX: QModelIndex = QModelIndex()
    NUMERIC_ALIGNMENT: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

    def __init__(self, palette: ClassPalette) -> None:
        """
        Parameters
        ----------
        palette : ClassPalette
            Colors of the classes.
        """
        super().__init__()
        self._palette: ClassPalette = palette
        self._records: list[DetectionRecord] = []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = ROOT_INDEX) -> int:
        return 0 if parent.isValid() else len(self._records)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = ROOT_INDEX) -> int:
        return 0 if parent.isValid() else len(ResultColumn)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if orientation != Qt.Orientation.Horizontal or role != Qt.ItemDataRole.DisplayRole:
            return None
        return ResultColumn(section).header

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        record: DetectionRecord = self._records[index.row()]
        column: ResultColumn = ResultColumn(index.column())
        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_text(record, column)
        if role == self.SORT_ROLE:
            return self._sort_value(record, column)
        if role == Qt.ItemDataRole.DecorationRole and column == ResultColumn.CLASS:
            return self._palette.swatch_of(record.detection.class_id)
        if role == Qt.ItemDataRole.ToolTipRole and column == ResultColumn.IMAGE:
            return str(record.image_path)
        if role == Qt.ItemDataRole.TextAlignmentRole and column.is_numeric:
            return self.NUMERIC_ALIGNMENT
        return None

    @property
    def records(self) -> tuple[DetectionRecord, ...]:
        """
        Listed detections in row order.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Every row.
        """
        return tuple(self._records)

    def record_at(self, row: int) -> DetectionRecord:
        """
        Detection of one row.

        Parameters
        ----------
        row : int
            Row of this model.

        Returns
        -------
        DetectionRecord
            Detection shown in ``row``.

        Raises
        ------
        IndexError
            If ``row`` does not exist.
        """
        if not 0 <= row < len(self._records):
            raise IndexError(f"row must be in [0, {len(self._records)}). got {row}")
        return self._records[row]

    def replace_image(self, image_path: Path, records: Sequence[DetectionRecord]) -> None:
        """
        Replace the rows of one image.

        Parameters
        ----------
        image_path : Path
            Image whose previous rows are removed.
        records : Sequence[DetectionRecord]
            New detections of ``image_path``, appended at the end.

        Raises
        ------
        ValueError
            If a record belongs to another image.
        """
        if any(record.image_path != image_path for record in records):
            raise ValueError(f"every record must belong to {image_path}")
        old_rows: list[int] = [row for row, record in enumerate(self._records) if record.image_path == image_path]
        if old_rows:
            self.beginRemoveRows(QModelIndex(), old_rows[0], old_rows[-1])
            del self._records[old_rows[0] : old_rows[-1] + 1]
            self.endRemoveRows()
        if records:
            first_row: int = len(self._records)
            self.beginInsertRows(QModelIndex(), first_row, first_row + len(records) - 1)
            self._records.extend(records)
            self.endInsertRows()

    def clear(self) -> None:
        """
        Remove every row.
        """
        self.beginResetModel()
        self._records = []
        self.endResetModel()

    @staticmethod
    def _display_text(record: DetectionRecord, column: ResultColumn) -> str:
        match column:
            case ResultColumn.IMAGE:
                return record.image_path.name
            case ResultColumn.CLASS:
                return record.detection.class_name
            case ResultColumn.QUERY:
                return record.query_label
            case ResultColumn.CONFIDENCE:
                return f"{record.detection.confidence:.3f}"
            case ResultColumn.X1 | ResultColumn.Y1 | ResultColumn.X2 | ResultColumn.Y2:
                return f"{DetectionRecordModel._coordinate(record, column):.1f}"

    @staticmethod
    def _sort_value(record: DetectionRecord, column: ResultColumn) -> str | float:
        match column:
            case ResultColumn.IMAGE:
                return record.image_path.name.casefold()
            case ResultColumn.CLASS:
                return record.detection.class_name.casefold()
            case ResultColumn.QUERY:
                return record.query_label.casefold()
            case ResultColumn.CONFIDENCE:
                return record.detection.confidence
            case ResultColumn.X1 | ResultColumn.Y1 | ResultColumn.X2 | ResultColumn.Y2:
                return DetectionRecordModel._coordinate(record, column)

    @staticmethod
    def _coordinate(record: DetectionRecord, column: ResultColumn) -> float:
        return record.xyxy[column.value - ResultColumn.X1.value]
