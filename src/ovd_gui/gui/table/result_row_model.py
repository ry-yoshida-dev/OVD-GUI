from collections.abc import Mapping, Sequence
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QGuiApplication, QIcon, QPalette

from ...detection import DetectionCatalog, DetectionRecord, PromptChange
from ..class_palette import ClassPalette
from .analysis_state import AnalysisState
from .image_status_row import ImageStatusRow
from .outdated_icon import OutdatedIcon
from .result_column import ResultColumn
from .result_row import ResultRow


class ResultRowModel(QAbstractTableModel):
    """
    Every open image with its detections, one detection per row.

    An image without any detection to list, not analyzed yet or detected without result, keeps one
    ``ImageStatusRow`` saying so. Rows of one image stay contiguous, in the order the images were opened; replacing
    the result of an image keeps its place. Rows of the current image are highlighted. The image cell of an image
    detected with other classes than the current ones carries a warning icon, and its tool tip names the change.
    ``SORT_ROLE`` gives raw values so that numbers sort numerically and image names case-insensitively.

    The ``Keep`` column of a detection is a check box telling whether the detection is exported; unchecking it
    rejects the detection in the catalog of the listed results, and rejected rows are greyed out and struck through.

    Signals
    -------
    acceptance_changed : Signal(Path)
        Detections of an image were accepted or rejected.
    """

    acceptance_changed: Signal = Signal(Path)

    SORT_ROLE: int = Qt.ItemDataRole.UserRole.value
    ROOT_INDEX: QModelIndex = QModelIndex()
    NUMERIC_ALIGNMENT: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    MISSING_NUMBER: float = -1.0
    CURRENT_IMAGE_HIGHLIGHT_ALPHA: int = 70
    KEPT_TEXT = "Kept"
    REJECTED_TEXT = "Rejected"

    def __init__(self, palette: ClassPalette) -> None:
        """
        Parameters
        ----------
        palette : ClassPalette
            Colors of the classes.
        """
        super().__init__()
        self._palette: ClassPalette = palette
        self._rows: list[ResultRow] = []
        self._image_paths: list[Path] = []
        self._catalog: DetectionCatalog | None = None
        self._current_image_path: Path | None = None
        self._prompt_changes: dict[Path, PromptChange] = {}
        self._outdated_icon: QIcon = OutdatedIcon().to_icon()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = ROOT_INDEX) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = ROOT_INDEX) -> int:
        return 0 if parent.isValid() else len(ResultColumn)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if orientation != Qt.Orientation.Horizontal or role != Qt.ItemDataRole.DisplayRole:
            return None
        return ResultColumn(section).header_label

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        row: ResultRow = self._rows[index.row()]
        column: ResultColumn = ResultColumn(index.column())
        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_text(row, column)
        if role == Qt.ItemDataRole.CheckStateRole and column == ResultColumn.ACCEPTED:
            return self._check_state_of(row)
        if role == self.SORT_ROLE:
            return self._sort_value(row, column) if column != ResultColumn.ACCEPTED else self.cell_text(row, column)
        if role == Qt.ItemDataRole.ToolTipRole and column == ResultColumn.ACCEPTED and isinstance(row, DetectionRecord):
            return "Checked detections are exported; uncheck to reject this detection"
        if role == Qt.ItemDataRole.ToolTipRole and column == ResultColumn.IMAGE:
            return self._image_tool_tip(row.image_path)
        if role == Qt.ItemDataRole.DecorationRole and column == ResultColumn.IMAGE and self.is_outdated(row):
            return self._outdated_icon
        if role == Qt.ItemDataRole.TextAlignmentRole and column.is_numeric:
            return self.NUMERIC_ALIGNMENT
        if role == Qt.ItemDataRole.BackgroundRole and self.is_current(row):
            return self._current_image_brush()
        if role == Qt.ItemDataRole.FontRole:
            return self._font_of(row)
        match row:
            case DetectionRecord():
                if role == Qt.ItemDataRole.DecorationRole and column == ResultColumn.CLASS:
                    return self._palette.swatch_of(row.detection.class_id)
                if role == Qt.ItemDataRole.ForegroundRole and not self.is_accepted(row):
                    return QGuiApplication.palette().brush(QPalette.ColorRole.PlaceholderText)
            case ImageStatusRow():
                if role == Qt.ItemDataRole.ForegroundRole:
                    return QGuiApplication.palette().brush(QPalette.ColorRole.PlaceholderText)
        return None

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        item_flags: Qt.ItemFlag = super().flags(index)
        if (
            index.isValid()
            and index.column() == ResultColumn.ACCEPTED.value
            and isinstance(self._rows[index.row()], DetectionRecord)
        ):
            item_flags |= Qt.ItemFlag.ItemIsUserCheckable
        return item_flags

    def setData(
        self, index: QModelIndex | QPersistentModelIndex, value: object, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if not index.isValid() or index.column() != ResultColumn.ACCEPTED.value:
            return False
        if role != Qt.ItemDataRole.CheckStateRole or not isinstance(value, int | Qt.CheckState):
            return False
        row: ResultRow = self._rows[index.row()]
        if not isinstance(row, DetectionRecord) or self._catalog is None:
            return False
        self.set_accepted((row,), Qt.CheckState(value) == Qt.CheckState.Checked)
        return True

    @property
    def catalog(self) -> DetectionCatalog | None:
        """
        Results whose detections are listed.

        Returns
        -------
        DetectionCatalog | None
            ``None`` while no profile is shown.
        """
        return self._catalog

    def is_accepted(self, row: ResultRow) -> bool:
        """
        Whether a row is kept for export.

        Parameters
        ----------
        row : ResultRow
            Row to test.

        Returns
        -------
        bool
            False for a rejected detection; True for other detections and for image status rows.
        """
        match row:
            case DetectionRecord():
                return self._catalog is None or self._catalog.is_accepted(row)
            case ImageStatusRow():
                return True

    def set_accepted(self, records: Sequence[DetectionRecord], is_accepted: bool) -> None:
        """
        Accept or reject listed detections, updating their check boxes.

        Parameters
        ----------
        records : Sequence[DetectionRecord]
            Listed detections.
        is_accepted : bool
            True to accept them, False to reject them.

        Raises
        ------
        RuntimeError
            If no catalog is listed.
        """
        if self._catalog is None:
            raise RuntimeError("no results are listed")
        indices_by_image: dict[Path, list[int]] = {}
        for record in records:
            indices_by_image.setdefault(record.image_path, []).append(record.detection_index)
        for image_path, detection_indices in indices_by_image.items():
            self._catalog.set_accepted(image_path, detection_indices, is_accepted)
            row_numbers: list[int] = self._row_numbers_of(image_path)
            if row_numbers:
                self.dataChanged.emit(self.index(row_numbers[0], 0), self.index(row_numbers[-1], len(ResultColumn) - 1))
            self.acceptance_changed.emit(image_path)

    @property
    def rows(self) -> tuple[ResultRow, ...]:
        """
        Listed rows in model order.

        Returns
        -------
        tuple[ResultRow, ...]
            Detections and image status rows.
        """
        return tuple(self._rows)

    @property
    def records(self) -> tuple[DetectionRecord, ...]:
        """
        Listed detections in row order.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Every detection row.
        """
        return tuple(row for row in self._rows if isinstance(row, DetectionRecord))

    @property
    def current_image_path(self) -> Path | None:
        """
        Image whose rows are highlighted.

        Returns
        -------
        Path | None
            Shown image, or ``None`` when no image is open.
        """
        return self._current_image_path

    def is_current(self, row: ResultRow) -> bool:
        """
        Whether a row belongs to the shown image.

        Parameters
        ----------
        row : ResultRow
            Row to test.

        Returns
        -------
        bool
            True if ``row`` is highlighted.
        """
        return self._current_image_path is not None and row.image_path == self._current_image_path

    @property
    def outdated_image_paths(self) -> tuple[Path, ...]:
        """
        Listed images detected with other classes than the current ones.

        Returns
        -------
        tuple[Path, ...]
            Outdated images in the order they were opened.
        """
        return tuple(image_path for image_path in self._image_paths if image_path in self._prompt_changes)

    def is_outdated(self, row: ResultRow) -> bool:
        """
        Whether a row belongs to an image detected with other classes than the current ones.

        Parameters
        ----------
        row : ResultRow
            Row to test.

        Returns
        -------
        bool
            True if the image of ``row`` carries a warning icon.
        """
        return row.image_path in self._prompt_changes

    def prompt_change_of(self, image_path: Path) -> PromptChange | None:
        """
        How the classes have changed since one image was detected.

        Parameters
        ----------
        image_path : Path
            Image to look up.

        Returns
        -------
        PromptChange | None
            ``None`` if the image is not outdated.
        """
        return self._prompt_changes.get(image_path)

    def set_prompt_changes(self, prompt_changes: Mapping[Path, PromptChange]) -> None:
        """
        Mark the images detected with other classes than the current ones.

        Parameters
        ----------
        prompt_changes : Mapping[Path, PromptChange]
            Change of every outdated image; other images are marked current.
        """
        previous_changes: dict[Path, PromptChange] = self._prompt_changes
        self._prompt_changes = {
            image_path: change for image_path, change in prompt_changes.items() if not change.is_unchanged
        }
        for image_path in previous_changes.keys() | self._prompt_changes.keys():
            if previous_changes.get(image_path) != self._prompt_changes.get(image_path):
                self._emit_rows_changed(image_path)

    def row_at(self, row: int) -> ResultRow:
        """
        Content of one row.

        Parameters
        ----------
        row : int
            Row of this model.

        Returns
        -------
        ResultRow
            Detection or image status shown in ``row``.

        Raises
        ------
        IndexError
            If ``row`` does not exist.
        """
        if not 0 <= row < len(self._rows):
            raise IndexError(f"row must be in [0, {len(self._rows)}). got {row}")
        return self._rows[row]

    def cell_text(self, row: ResultRow, column: ResultColumn) -> str:
        """
        Text of one cell, as filtered by value.

        Parameters
        ----------
        row : ResultRow
            Row of the cell.
        column : ResultColumn
            Column of the cell.

        Returns
        -------
        str
            Displayed text; ``Kept`` or ``Rejected`` for the check box of a detection; empty for a blank cell.
        """
        if column == ResultColumn.ACCEPTED and isinstance(row, DetectionRecord):
            return self.KEPT_TEXT if self.is_accepted(row) else self.REJECTED_TEXT
        return self._display_text(row, column)

    @staticmethod
    def cell_number(row: ResultRow, column: ResultColumn) -> float | None:
        """
        Unrounded number of one numeric cell.

        Parameters
        ----------
        row : ResultRow
            Row of the cell.
        column : ResultColumn
            Numeric column of the cell.

        Returns
        -------
        float | None
            Confidence or box coordinate, or ``None`` for a row without detection.

        Raises
        ------
        ValueError
            If ``column`` is not numeric.
        """
        if not column.is_numeric:
            raise ValueError(f"{column.header} is not a numeric column")
        match row:
            case ImageStatusRow():
                return None
            case DetectionRecord():
                return float(ResultRowModel._record_sort_value(row, column))

    def add_images(self, image_paths: Sequence[Path]) -> None:
        """
        List newly opened images with their stored detections, or as not analyzed.

        Parameters
        ----------
        image_paths : Sequence[Path]
            Opened images; images already listed are left as they are.
        """
        for image_path in image_paths:
            if image_path not in self._image_paths:
                self._replace_rows(image_path, self._rows_from(self._catalog, image_path))

    def replace_image(self, image_path: Path, records: Sequence[DetectionRecord]) -> None:
        """
        Replace the rows of one image with its new detections.

        Parameters
        ----------
        image_path : Path
            Detected image; an image not listed yet is appended.
        records : Sequence[DetectionRecord]
            New detections of ``image_path``; none lists the image as detected without result.

        Raises
        ------
        ValueError
            If a record belongs to another image.
        """
        if any(record.image_path != image_path for record in records):
            raise ValueError(f"every record must belong to {image_path}")
        new_rows: tuple[ResultRow, ...] = (
            tuple(records) if records else (ImageStatusRow(image_path, AnalysisState.NO_DETECTIONS),)
        )
        self._replace_rows(image_path, new_rows)

    def remove_images(self, image_paths: Sequence[Path]) -> None:
        """
        Stop listing some images.

        Parameters
        ----------
        image_paths : Sequence[Path]
            Images to remove; images not listed are ignored.
        """
        for image_path in image_paths:
            if image_path not in self._image_paths:
                continue
            row_numbers: list[int] = self._row_numbers_of(image_path)
            if row_numbers:
                self.beginRemoveRows(QModelIndex(), row_numbers[0], row_numbers[-1])
                del self._rows[row_numbers[0] : row_numbers[-1] + 1]
                self.endRemoveRows()
            self._image_paths.remove(image_path)
            self._prompt_changes.pop(image_path, None)
            if image_path == self._current_image_path:
                self._current_image_path = None

    def show_catalog(self, catalog: DetectionCatalog | None) -> None:
        """
        List the detections stored in a catalog in place of the current rows.

        Parameters
        ----------
        catalog : DetectionCatalog | None
            Results to list; images it holds no result for, or every image when ``None``, are listed as not
            analyzed.
        """
        self.beginResetModel()
        self._catalog = catalog
        self._rows = [row for image_path in self._image_paths for row in self._rows_from(catalog, image_path)]
        self._prompt_changes = {}
        self.endResetModel()

    def set_current_image(self, image_path: Path | None) -> None:
        """
        Highlight the rows of the shown image.

        Parameters
        ----------
        image_path : Path | None
            Shown image, or ``None`` when no image is open.
        """
        if image_path == self._current_image_path:
            return
        previous_image_path: Path | None = self._current_image_path
        self._current_image_path = image_path
        for changed_image_path in (previous_image_path, image_path):
            if changed_image_path is not None:
                self._emit_rows_changed(changed_image_path)

    @staticmethod
    def _rows_from(catalog: DetectionCatalog | None, image_path: Path) -> tuple[ResultRow, ...]:
        if catalog is None or image_path not in catalog:
            return (ImageStatusRow(image_path, AnalysisState.NOT_ANALYZED),)
        records: tuple[DetectionRecord, ...] = catalog.records_of(image_path)
        return records if records else (ImageStatusRow(image_path, AnalysisState.NO_DETECTIONS),)

    def _replace_rows(self, image_path: Path, new_rows: Sequence[ResultRow]) -> None:
        old_rows: list[int] = self._row_numbers_of(image_path)
        insert_row: int = old_rows[0] if old_rows else len(self._rows)
        if old_rows:
            self.beginRemoveRows(QModelIndex(), old_rows[0], old_rows[-1])
            del self._rows[old_rows[0] : old_rows[-1] + 1]
            self.endRemoveRows()
        else:
            self._image_paths.append(image_path)
        if new_rows:
            self.beginInsertRows(QModelIndex(), insert_row, insert_row + len(new_rows) - 1)
            self._rows[insert_row:insert_row] = new_rows
            self.endInsertRows()

    def _row_numbers_of(self, image_path: Path) -> list[int]:
        return [row_number for row_number, row in enumerate(self._rows) if row.image_path == image_path]

    def _emit_rows_changed(self, image_path: Path) -> None:
        row_numbers: list[int] = self._row_numbers_of(image_path)
        if row_numbers:
            self.dataChanged.emit(
                self.index(row_numbers[0], 0),
                self.index(row_numbers[-1], len(ResultColumn) - 1),
                [
                    Qt.ItemDataRole.BackgroundRole,
                    Qt.ItemDataRole.FontRole,
                    Qt.ItemDataRole.DecorationRole,
                    Qt.ItemDataRole.ToolTipRole,
                ],
            )

    def _image_tool_tip(self, image_path: Path) -> str:
        change: PromptChange | None = self._prompt_changes.get(image_path)
        if change is None:
            return str(image_path)
        return f"{image_path}\nDetected with other classes: {change.description}"

    def _current_image_brush(self) -> QBrush:
        color: QColor = QGuiApplication.palette().color(QPalette.ColorRole.Highlight)
        color.setAlpha(self.CURRENT_IMAGE_HIGHLIGHT_ALPHA)
        return QBrush(color)

    def _font_of(self, row: ResultRow) -> QFont:
        font: QFont = QFont()
        font.setBold(self.is_current(row))
        font.setItalic(isinstance(row, ImageStatusRow))
        font.setStrikeOut(not self.is_accepted(row))
        return font

    def _check_state_of(self, row: ResultRow) -> Qt.CheckState | None:
        match row:
            case DetectionRecord():
                return Qt.CheckState.Checked if self.is_accepted(row) else Qt.CheckState.Unchecked
            case ImageStatusRow():
                return None

    @staticmethod
    def _display_text(row: ResultRow, column: ResultColumn) -> str:
        match row:
            case ImageStatusRow():
                match column:
                    case ResultColumn.IMAGE:
                        return row.image_path.name
                    case ResultColumn.CLASS:
                        return row.state.label
                    case _:
                        return ""
            case DetectionRecord():
                return ResultRowModel._record_text(row, column)

    @staticmethod
    def _record_text(record: DetectionRecord, column: ResultColumn) -> str:
        match column:
            case ResultColumn.ACCEPTED:
                return ""
            case ResultColumn.IMAGE:
                return record.image_path.name
            case ResultColumn.CLASS:
                return record.detection.class_name
            case ResultColumn.QUERY:
                return record.query_label
            case ResultColumn.CONFIDENCE:
                return f"{record.detection.confidence:.3f}"
            case ResultColumn.X1 | ResultColumn.Y1 | ResultColumn.X2 | ResultColumn.Y2:
                return f"{ResultRowModel._coordinate(record, column):.1f}"

    @staticmethod
    def _sort_value(row: ResultRow, column: ResultColumn) -> str | float:
        match row:
            case ImageStatusRow():
                if column == ResultColumn.IMAGE:
                    return row.image_path.name.casefold()
                return ResultRowModel.MISSING_NUMBER if column.is_numeric else ""
            case DetectionRecord():
                return ResultRowModel._record_sort_value(row, column)

    @staticmethod
    def _record_sort_value(record: DetectionRecord, column: ResultColumn) -> str | float:
        match column:
            case ResultColumn.ACCEPTED:
                return ""
            case ResultColumn.IMAGE:
                return record.image_path.name.casefold()
            case ResultColumn.CLASS:
                return record.detection.class_name.casefold()
            case ResultColumn.QUERY:
                return record.query_label.casefold()
            case ResultColumn.CONFIDENCE:
                return record.detection.confidence
            case ResultColumn.X1 | ResultColumn.Y1 | ResultColumn.X2 | ResultColumn.Y2:
                return ResultRowModel._coordinate(record, column)

    @staticmethod
    def _coordinate(record: DetectionRecord, column: ResultColumn) -> float:
        return record.xyxy[column.value - ResultColumn.X1.value]
