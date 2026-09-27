from collections.abc import Collection, Sequence
from pathlib import Path

from PySide6.QtCore import QItemSelection, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...detection import DetectionFilter, DetectionRecord
from ..class_palette import ClassPalette
from .analysis_state import AnalysisState
from .class_filter_button import ClassFilterButton
from .image_status_row import ImageStatusRow
from .result_column import ResultColumn
from .result_filter_proxy_model import ResultFilterProxyModel
from .result_row import ResultRow
from .result_row_model import ResultRowModel


class ResultPanel(QWidget):
    """
    Searchable table of the detections of every open image.

    An image without any detection to list says whether it is not analyzed yet or has no detections, and the rows of
    the shown image are highlighted. Rows are narrowed by any number of classes, chosen from a funnel button, image file name and minimum confidence, and sorted by
    clicking a column header. Selecting a row reports its detection, or its image for an image without detections,
    so that the window can show the image and highlight the box.

    Signals
    -------
    detection_selected : Signal(DetectionRecord)
        A detection row was selected.
    image_selected : Signal(Path)
        The row of an image without detections was selected.
    selection_cleared : Signal()
        No row is selected any more.
    clear_requested : Signal()
        The user asked to forget every result.
    """

    detection_selected: Signal = Signal(DetectionRecord)
    image_selected: Signal = Signal(Path)
    selection_cleared: Signal = Signal()
    clear_requested: Signal = Signal()

    CONFIDENCE_STEP = 0.05

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

        self._class_filter_button: ClassFilterButton = ClassFilterButton()
        self._image_name_edit: QLineEdit = QLineEdit()
        self._image_name_edit.setPlaceholderText("Filter image names")
        self._image_name_edit.setClearButtonEnabled(True)
        self._confidence_spin: QDoubleSpinBox = QDoubleSpinBox()
        self._confidence_spin.setRange(0.0, 1.0)
        self._confidence_spin.setSingleStep(self.CONFIDENCE_STEP)
        self._confidence_spin.setDecimals(2)
        self._confidence_spin.setPrefix("Conf ≥ ")
        self._confidence_spin.setToolTip("Only detections at least this confident")
        self._table_view: QTableView = QTableView()
        self._summary_label: QLabel = QLabel()
        self._clear_button: QPushButton = QPushButton("Clear Results")
        self._clear_button.setToolTip("Forget the results of every image")

        self._build_table_view()
        self._build_layout()
        self._connect_signals()
        self._apply_filter()

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

    def set_class_filter(self, class_names: Collection[str]) -> None:
        """
        List only the detections of some classes.

        Parameters
        ----------
        class_names : Collection[str]
            Classes to keep; empty lists every class.

        Raises
        ------
        KeyError
            If no listed detection has one of ``class_names``.
        """
        self._class_filter_button.set_selected_class_names(class_names)

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
        self._refresh_class_choices()
        self._update_summary()

    def clear_results(self) -> None:
        """
        Forget every detection, listing every image as not analyzed again.
        """
        self._table_model.clear_results()
        self._refresh_class_choices()
        self._update_summary()

    def _build_table_view(self) -> None:
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
        filter_row: QHBoxLayout = QHBoxLayout()
        filter_row.addWidget(self._class_filter_button)
        filter_row.addWidget(self._image_name_edit, stretch=1)
        filter_row.addWidget(self._confidence_spin)
        footer_row: QHBoxLayout = QHBoxLayout()
        footer_row.addWidget(self._summary_label, stretch=1)
        footer_row.addWidget(self._clear_button)
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(filter_row)
        layout.addWidget(self._table_view, stretch=1)
        layout.addLayout(footer_row)

    def _connect_signals(self) -> None:
        self._class_filter_button.selection_changed.connect(self._apply_filter)
        self._image_name_edit.textChanged.connect(self._apply_filter)
        self._confidence_spin.valueChanged.connect(self._apply_filter)
        self._clear_button.clicked.connect(self.clear_requested)
        self._table_view.selectionModel().selectionChanged.connect(self._emit_selection)
        self._proxy_model.rowsInserted.connect(self._update_summary)
        self._proxy_model.rowsRemoved.connect(self._update_summary)
        self._proxy_model.modelReset.connect(self._update_summary)

    def _apply_filter(self) -> None:
        self._proxy_model.set_detection_filter(
            DetectionFilter(
                class_names=self._class_filter_button.selected_class_names,
                image_name_text=self._image_name_edit.text(),
                minimum_confidence=self._confidence_spin.value(),
            )
        )
        self._update_summary()

    def _refresh_class_choices(self) -> None:
        self._class_filter_button.set_class_names({record.detection.class_name for record in self._table_model.records})

    def _update_summary(self) -> None:
        visible_count: int = len(self.visible_records)
        total_count: int = len(self._table_model.records)
        not_analyzed_count: int = sum(
            1
            for row in self._table_model.rows
            if isinstance(row, ImageStatusRow) and row.state == AnalysisState.NOT_ANALYZED
        )
        not_analyzed_note: str = f" · {not_analyzed_count} not analyzed" if not_analyzed_count else ""
        self._summary_label.setText(f"{visible_count} / {total_count} detections{not_analyzed_note}")
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
