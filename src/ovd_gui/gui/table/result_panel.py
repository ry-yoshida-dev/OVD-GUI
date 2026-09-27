from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QItemSelection, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
from .detection_filter_proxy_model import DetectionFilterProxyModel
from .detection_record_model import DetectionRecordModel
from .result_column import ResultColumn
from .result_scope import ResultScope


class ResultPanel(QWidget):
    """
    Searchable table of the detections of the current image or of every detected image.

    Detections are narrowed by scope, class, image file name and minimum confidence, and sorted by clicking a column
    header. Selecting a row reports its detection so that the window can show its image and highlight its box.

    Signals
    -------
    detection_selected : Signal(DetectionRecord)
        A row was selected.
    selection_cleared : Signal()
        No row is selected any more.
    clear_requested : Signal()
        The user asked to forget every result.
    """

    detection_selected: Signal = Signal(DetectionRecord)
    selection_cleared: Signal = Signal()
    clear_requested: Signal = Signal()

    ALL_CLASSES_LABEL = "All classes"
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
        self._current_image_path: Path | None = None
        self._table_model: DetectionRecordModel = DetectionRecordModel(palette)
        self._proxy_model: DetectionFilterProxyModel = DetectionFilterProxyModel(self._table_model)

        self._scope_combo: QComboBox = QComboBox()
        for scope in ResultScope:
            self._scope_combo.addItem(scope.label, scope)
        self._class_combo: QComboBox = QComboBox()
        self._class_combo.addItem(self.ALL_CLASSES_LABEL, None)
        self._class_combo.setToolTip("Only detections of this class")
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
    def scope(self) -> ResultScope:
        """
        Which images are listed.

        Returns
        -------
        ResultScope
            Selected scope.
        """
        return ResultScope(self._scope_combo.currentData())

    @property
    def visible_records(self) -> tuple[DetectionRecord, ...]:
        """
        Listed detections in display order.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Rows passing the filters, sorted as shown.
        """
        return self._proxy_model.visible_records()

    def set_scope(self, scope: ResultScope) -> None:
        """
        Choose which images are listed.

        Parameters
        ----------
        scope : ResultScope
            Scope to select.
        """
        self._scope_combo.setCurrentIndex(self._scope_combo.findData(scope))

    def set_class_filter(self, class_name: str | None) -> None:
        """
        List only the detections of one class.

        Parameters
        ----------
        class_name : str | None
            Class to keep; ``None`` lists every class.

        Raises
        ------
        KeyError
            If no listed detection has ``class_name``.
        """
        index: int = self._class_combo.findData(class_name)
        if index < 0:
            raise KeyError(class_name)
        self._class_combo.setCurrentIndex(index)

    def set_current_image(self, image_path: Path | None) -> None:
        """
        Follow the image shown in the window.

        Parameters
        ----------
        image_path : Path | None
            Shown image, or ``None`` when no image is open.
        """
        self._current_image_path = image_path
        self._apply_filter()

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

    def clear(self) -> None:
        """
        Remove every detection.
        """
        self._table_model.clear()
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
        header.setSectionResizeMode(ResultColumn.IMAGE.value, QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setSortIndicatorShown(True)

    def _build_layout(self) -> None:
        scope_row: QHBoxLayout = QHBoxLayout()
        scope_row.addWidget(self._scope_combo, stretch=1)
        scope_row.addWidget(self._class_combo, stretch=1)
        filter_row: QHBoxLayout = QHBoxLayout()
        filter_row.addWidget(self._image_name_edit, stretch=1)
        filter_row.addWidget(self._confidence_spin)
        footer_row: QHBoxLayout = QHBoxLayout()
        footer_row.addWidget(self._summary_label, stretch=1)
        footer_row.addWidget(self._clear_button)
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(scope_row)
        layout.addLayout(filter_row)
        layout.addWidget(self._table_view, stretch=1)
        layout.addLayout(footer_row)

    def _connect_signals(self) -> None:
        self._scope_combo.currentIndexChanged.connect(self._apply_filter)
        self._class_combo.currentIndexChanged.connect(self._apply_filter)
        self._image_name_edit.textChanged.connect(self._apply_filter)
        self._confidence_spin.valueChanged.connect(self._apply_filter)
        self._clear_button.clicked.connect(self.clear_requested)
        self._table_view.selectionModel().selectionChanged.connect(self._emit_selection)
        self._proxy_model.rowsInserted.connect(self._update_summary)
        self._proxy_model.rowsRemoved.connect(self._update_summary)
        self._proxy_model.modelReset.connect(self._update_summary)

    def _apply_filter(self) -> None:
        image_path: Path | None
        match self.scope:
            case ResultScope.CURRENT_IMAGE:
                image_path = self._current_image_path if self._current_image_path is not None else Path()
            case ResultScope.ALL_IMAGES:
                image_path = None
        selected_class: object = self._class_combo.currentData()
        self._proxy_model.set_detection_filter(
            DetectionFilter(
                image_path=image_path,
                class_name=selected_class if isinstance(selected_class, str) else None,
                image_name_text=self._image_name_edit.text(),
                minimum_confidence=self._confidence_spin.value(),
            )
        )
        self._update_summary()

    def _refresh_class_choices(self) -> None:
        selected_class: object = self._class_combo.currentData()
        class_names: list[str] = sorted({record.detection.class_name for record in self._table_model.records})
        if isinstance(selected_class, str) and selected_class not in class_names:
            class_names = sorted([*class_names, selected_class])
        self._class_combo.blockSignals(True)
        self._class_combo.clear()
        self._class_combo.addItem(self.ALL_CLASSES_LABEL, None)
        for class_name in class_names:
            self._class_combo.addItem(class_name, class_name)
        self._class_combo.setCurrentIndex(max(self._class_combo.findData(selected_class), 0))
        self._class_combo.blockSignals(False)

    def _update_summary(self) -> None:
        visible_records: tuple[DetectionRecord, ...] = self._proxy_model.visible_records()
        image_count: int = len({record.image_path for record in visible_records})
        total_count: int = self._table_model.rowCount()
        self._summary_label.setText(
            f"{len(visible_records)} / {total_count} detections in {image_count} image{'' if image_count == 1 else 's'}"
        )
        self._clear_button.setEnabled(total_count > 0)

    def _emit_selection(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        selected_rows: list[int] = sorted({index.row() for index in self._table_view.selectionModel().selectedRows()})
        if selected_rows:
            self.detection_selected.emit(self._proxy_model.record_at(selected_rows[0]))
        else:
            self.selection_cleared.emit()
