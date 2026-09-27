from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QItemSelection, QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...detection import DetectionCatalog, DetectionRecord
from ..class_palette import ClassPalette
from .analysis_state import AnalysisState
from .column_condition import ColumnCondition
from .column_filter_popup import ColumnFilterPopup
from .filter_header_view import FilterHeaderView
from .image_status_row import ImageStatusRow
from .range_condition import RangeCondition
from .range_editor import RangeEditor
from .result_column import ResultColumn
from .result_filter_proxy_model import ResultFilterProxyModel
from .result_row import ResultRow
from .result_row_model import ResultRowModel
from .table_filter import TableFilter
from .value_checklist import ValueChecklist
from .value_condition import ValueCondition


class ResultPanel(QWidget):
    """
    Filterable table of the detections of every open image.

    An image without any detection to list says whether it is not analyzed yet or has no detections, and the rows of
    the shown image are highlighted. Every column can be filtered from the funnel in its header, or by right-clicking
    the header: text columns by checking values, numeric columns by lower and upper bounds. A row is listed when it
    passes the filters of every column; clicking the rest of a header sorts. The table lists the results of one
    detector profile at a time, chosen by the window. Selecting a row reports its detection, or its image for an
    image without detections, so that the window can show the image and highlight the box.

    Signals
    -------
    detection_selected : Signal(DetectionRecord)
        A detection row was selected.
    image_selected : Signal(Path)
        The row of an image without detections was selected.
    selection_cleared : Signal()
        No row is selected any more.
    clear_requested : Signal()
        The user asked to forget the results of every model.
    """

    detection_selected: Signal = Signal(DetectionRecord)
    image_selected: Signal = Signal(Path)
    selection_cleared: Signal = Signal()
    clear_requested: Signal = Signal()

    def __init__(self, palette: ClassPalette, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        palette : ClassPalette
            Colors of the classes.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._table_model: ResultRowModel = ResultRowModel(palette)
        self._proxy_model: ResultFilterProxyModel = ResultFilterProxyModel(self._table_model)

        self._header_view: FilterHeaderView = FilterHeaderView()
        self._table_view: QTableView = QTableView()
        self._summary_label: QLabel = QLabel()
        self._clear_filters_button: QPushButton = QPushButton("Clear Filters")
        self._clear_filters_button.setToolTip("List every row again")
        self._clear_button: QPushButton = QPushButton("Clear Results")
        self._clear_button.setToolTip("Forget the results of every model")

        self._build_table_view()
        self._build_layout()
        self._connect_signals()
        self._update_summary()

    @property
    def visible_rows(self) -> tuple[ResultRow, ...]:
        """
        Listed rows in display order.

        Returns
        -------
        tuple[ResultRow, ...]
            Detections and image status rows passing the filters, sorted as shown.
        """
        return self._proxy_model.visible_rows()

    @property
    def visible_records(self) -> tuple[DetectionRecord, ...]:
        """
        Listed detections in display order.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Detection rows passing the filters, sorted as shown.
        """
        return tuple(row for row in self.visible_rows if isinstance(row, DetectionRecord))

    @property
    def table_filter(self) -> TableFilter:
        """
        Conditions of the listed rows.

        Returns
        -------
        TableFilter
            Filter of every column.
        """
        return self._proxy_model.table_filter

    def set_column_filter(self, column: ResultColumn, condition: ColumnCondition | None) -> None:
        """
        Filter one column, keeping the filters of the others.

        Parameters
        ----------
        column : ResultColumn
            Column to filter.
        condition : ColumnCondition | None
            Condition of the column; ``None`` stops filtering it.

        Raises
        ------
        TypeError
            If the kind of ``condition`` does not suit the column: values for a text column, a range for a
            numeric one.
        """
        match condition:
            case ValueCondition() if column.is_numeric:
                raise TypeError(f"{column.header} is numeric and takes a RangeCondition")
            case RangeCondition() if not column.is_numeric:
                raise TypeError(f"{column.header} is textual and takes a ValueCondition")
            case _:
                pass
        self._proxy_model.set_table_filter(self._proxy_model.table_filter.with_condition(column, condition))
        self._update_summary()

    def clear_filters(self) -> None:
        """
        Stop filtering every column.
        """
        self._proxy_model.set_table_filter(TableFilter())
        self._update_summary()

    def open_filter_popup(self, column: ResultColumn, position: QPoint | None = None) -> ColumnFilterPopup:
        """
        Show the popup editing the filter of one column.

        Parameters
        ----------
        column : ResultColumn
            Column to filter.
        position : QPoint | None, optional
            Global position of the top-left corner of the popup; ``None`` places it under the column header.

        Returns
        -------
        ColumnFilterPopup
            Shown popup, deleted once closed.
        """
        editor: ValueChecklist | RangeEditor
        condition: ColumnCondition | None = self.table_filter.condition_of(column)
        if column.is_numeric:
            editor = RangeEditor(
                column,
                self._proxy_model.number_span(column),
                condition if isinstance(condition, RangeCondition) else None,
            )
        else:
            editor = ValueChecklist(
                self._proxy_model.candidate_texts(column),
                condition if isinstance(condition, ValueCondition) else None,
            )
        popup: ColumnFilterPopup = ColumnFilterPopup(column, editor, self)
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.condition_applied.connect(self.set_column_filter)
        if position is None:
            left: int = self._header_view.sectionViewportPosition(column.value)
            position = self._header_view.viewport().mapToGlobal(QPoint(left, self._header_view.height()))
        popup.move(position)
        popup.show()
        return popup

    def is_current(self, row: ResultRow) -> bool:
        """
        Whether a row is highlighted as belonging to the shown image.

        Parameters
        ----------
        row : ResultRow
            Row to test.

        Returns
        -------
        bool
            True if ``row`` belongs to the shown image.
        """
        return self._table_model.is_current(row)

    def add_images(self, image_paths: Sequence[Path]) -> None:
        """
        List newly opened images as not analyzed.

        Parameters
        ----------
        image_paths : Sequence[Path]
            Opened images; images already listed are left as they are.
        """
        self._table_model.add_images(image_paths)
        self._update_summary()

    def set_current_image(self, image_path: Path | None) -> None:
        """
        Highlight the rows of the image shown in the window and scroll them into view.

        Parameters
        ----------
        image_path : Path | None
            Shown image, or ``None`` when no image is open.
        """
        self._table_model.set_current_image(image_path)
        self._reveal_current_image()

    def replace_image(self, image_path: Path, records: Sequence[DetectionRecord]) -> None:
        """
        Show new detections of one image in place of its previous ones.

        Parameters
        ----------
        image_path : Path
            Detected image.
        records : Sequence[DetectionRecord]
            Detections of ``image_path``.
        """
        self._table_model.replace_image(image_path, records)
        self._update_summary()

    def show_catalog(self, catalog: DetectionCatalog | None) -> None:
        """
        List the detections of one detector profile in place of the current ones.

        Parameters
        ----------
        catalog : DetectionCatalog | None
            Results to list; ``None`` lists every image as not analyzed.
        """
        self._table_model.show_catalog(catalog)
        self._update_summary()

    def _build_table_view(self) -> None:
        self._table_view.setHorizontalHeader(self._header_view)
        self._table_view.setModel(self._proxy_model)
        self._table_view.setSortingEnabled(True)
        self._table_view.sortByColumn(-1, Qt.SortOrder.AscendingOrder)
        self._table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.verticalHeader().setVisible(False)
        header: QHeaderView = self._table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(ResultColumn.IMAGE.value, QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(False)
        header.setSortIndicatorShown(True)

    def _build_layout(self) -> None:
        footer_row: QHBoxLayout = QHBoxLayout()
        footer_row.addWidget(self._summary_label, stretch=1)
        footer_row.addWidget(self._clear_filters_button)
        footer_row.addWidget(self._clear_button)
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._table_view, stretch=1)
        layout.addLayout(footer_row)

    def _connect_signals(self) -> None:
        self._header_view.filter_requested.connect(self._on_filter_requested)
        self._clear_filters_button.clicked.connect(self.clear_filters)
        self._clear_button.clicked.connect(self.clear_requested)
        self._table_view.selectionModel().selectionChanged.connect(self._emit_selection)
        self._proxy_model.rowsInserted.connect(self._update_summary)
        self._proxy_model.rowsRemoved.connect(self._update_summary)
        self._proxy_model.modelReset.connect(self._update_summary)

    def _on_filter_requested(self, logical_index: int, position: QPoint) -> None:
        self.open_filter_popup(ResultColumn(logical_index), position)

    def _update_summary(self) -> None:
        visible_count: int = len(self.visible_records)
        total_count: int = len(self._table_model.records)
        not_analyzed_count: int = sum(
            1
            for row in self._table_model.rows
            if isinstance(row, ImageStatusRow) and row.state == AnalysisState.NOT_ANALYZED
        )
        not_analyzed_note: str = f" · {not_analyzed_count} not analyzed" if not_analyzed_count else ""
        filtered_headers: list[str] = [
            column.header for column in ResultColumn if self.table_filter.condition_of(column) is not None
        ]
        filter_note: str = f" · filtered by {', '.join(filtered_headers)}" if filtered_headers else ""
        self._summary_label.setText(f"{visible_count} / {total_count} detections{not_analyzed_note}{filter_note}")
        self._clear_filters_button.setEnabled(bool(filtered_headers))
        self._clear_button.setEnabled(not_analyzed_count < len(self._table_model.rows))

    def _reveal_current_image(self) -> None:
        selected_rows: list[int] = self._selected_proxy_rows()
        if selected_rows and self.is_current(self._proxy_model.row_at(selected_rows[0])):
            return
        current_rows: list[int] = [
            proxy_row
            for proxy_row in range(self._proxy_model.rowCount())
            if self.is_current(self._proxy_model.row_at(proxy_row))
        ]
        if current_rows:
            self._table_view.scrollTo(self._proxy_model.index(current_rows[0], 0))

    def _selected_proxy_rows(self) -> list[int]:
        return sorted({index.row() for index in self._table_view.selectionModel().selectedRows()})

    def _emit_selection(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        selected_rows: list[int] = self._selected_proxy_rows()
        if not selected_rows:
            self.selection_cleared.emit()
            return
        row: ResultRow = self._proxy_model.row_at(selected_rows[0])
        match row:
            case DetectionRecord():
                self.detection_selected.emit(row)
            case ImageStatusRow():
                self.image_selected.emit(row.image_path)
