from collections.abc import Callable, Mapping, Sequence
from functools import partial
from pathlib import Path

from PySide6.QtCore import QItemSelection, QItemSelectionModel, QPoint, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...detection import DetectionCatalog, DetectionRecord, PromptChange
from ...export import DetectionTableWriter
from ...review import ClassThresholds
from ..class_palette import ClassPalette
from .analysis_state import AnalysisState
from .column_auto_fit import ColumnAutoFit
from .column_condition import ColumnCondition
from .column_filter_popup import ColumnFilterPopup
from .filter_header_view import FilterHeaderView
from .funnel_icon import FunnelIcon
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
    the shown image are highlighted. Every column can be filtered from the ``Filter`` button, or by right-clicking
    the header: text columns by checking values, numeric columns by lower and upper bounds. A row is listed when it
    passes the filters of every column; clicking the rest of a header sorts. The table lists the results of one
    detector profile at a time, chosen by the window. Selecting a row reports its detection, or its image for an
    image without detections, so that the window can show the image and highlight the box. Only the user moves the
    selection to another row: when results arrive or filters change, the selected row stays selected if it is still
    listed, and the selection is cleared otherwise instead of moving to a row of another image.

    Images detected with other classes, phrases or reference boxes than the current ones keep their rows, marked
    with a warning icon whose tool tip names the change; ``Update Outdated`` asks to detect just those images again.

    Columns are as wide as their cells, never widened by their header text except to show the funnel of a filtered
    column; once the user drags a column edge, every width is kept as set. The ``Keep`` header shows a check mark.
    One ``Filter`` button lists the columns to filter; right-clicking a header filters its column directly.

    The ``Keep`` check box of a detection accepts or rejects it for export; Space toggles the selected detection,
    and the right-click menu keeps or rejects the selected detection or every listed one, e.g. after filtering the
    low confidences. Detections below the minimum confidence of their class are not listed.

    ``Save CSV…``, also in the right-click menu, saves the listed detections in display order as a CSV file.

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
    update_outdated_requested : Signal()
        The user asked to detect the outdated images again with the current classes.
    acceptance_changed : Signal(Path)
        Detections of an image were kept or rejected.
    listing_changed : Signal()
        The listed rows may have changed: new results, filters, thresholds, removed images or rejections.
    message_posted : Signal(str)
        A short notice for the status bar, e.g. that the table was saved.
    """

    detection_selected: Signal = Signal(DetectionRecord)
    image_selected: Signal = Signal(Path)
    selection_cleared: Signal = Signal()
    clear_requested: Signal = Signal()
    update_outdated_requested: Signal = Signal()
    acceptance_changed: Signal = Signal(Path)
    listing_changed: Signal = Signal()
    message_posted: Signal = Signal(str)

    TABLE_FILE_SUFFIX = ".csv"
    DEFAULT_TABLE_FILE_NAME = f"detections{TABLE_FILE_SUFFIX}"

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
        self._summary_label.setWordWrap(True)
        self._funnel_icons: dict[bool, QIcon] = {
            is_filtered: FunnelIcon(
                QGuiApplication.palette().color(
                    QPalette.ColorRole.Highlight if is_filtered else QPalette.ColorRole.PlaceholderText
                ),
                is_filtered,
            ).to_icon()
            for is_filtered in (False, True)
        }
        self._filter_menu: QMenu = QMenu(self)
        self._filter_button: QToolButton = QToolButton()
        self._filter_button.setText("Filter")
        self._filter_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._filter_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._filter_button.setMenu(self._filter_menu)
        self._filter_button.setToolTip("Filter a column; right-clicking a column header does the same")
        self._save_table_button: QPushButton = QPushButton("Save CSV…")
        self._save_table_button.setToolTip("Save the listed detections as a CSV file")
        self._table_path: Path = Path(self.DEFAULT_TABLE_FILE_NAME)
        self._clear_filters_button: QPushButton = QPushButton("Clear Filters")
        self._clear_filters_button.setToolTip("List every row again")
        self._update_outdated_button: QPushButton = QPushButton("Update Outdated")
        self._update_outdated_button.setToolTip("Detect the images marked outdated again with the current classes")
        self._clear_button: QPushButton = QPushButton("Clear Results")
        self._clear_button.setToolTip("Forget the results of every model")
        self._is_updating_rows: bool = False
        self._column_auto_fit: ColumnAutoFit = ColumnAutoFit(self._header_view, self._default_column_width)
        self._toggle_action: QAction = QAction("Keep / Reject", self)
        self._toggle_action.setShortcut(QKeySequence(Qt.Key.Key_Space))
        self._toggle_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._keep_listed_action: QAction = QAction("Keep All Listed", self)
        self._reject_listed_action: QAction = QAction("Reject All Listed", self)

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
    def selected_record(self) -> DetectionRecord | None:
        """
        Detection of the selected row.

        Returns
        -------
        DetectionRecord | None
            ``None`` while no detection row is selected.
        """
        row: ResultRow | None = self._selected_row()
        return row if isinstance(row, DetectionRecord) else None

    def listed_detection_indices(self, image_path: Path) -> frozenset[int]:
        """
        Detections of one image listed in the table.

        Parameters
        ----------
        image_path : Path
            Image to look up.

        Returns
        -------
        frozenset[int]
            Indices of its detections passing the filters and the class minimums.
        """
        return frozenset(record.detection_index for record in self.visible_records if record.image_path == image_path)

    def listed_detection_indices_by_image(self) -> dict[Path, frozenset[int]]:
        """
        Detections listed in the table, grouped by image.

        Returns
        -------
        dict[Path, frozenset[int]]
            Indices of the listed detections of every image with at least one listed detection.
        """
        indices_by_image: dict[Path, set[int]] = {}
        for record in self.visible_records:
            indices_by_image.setdefault(record.image_path, set()).add(record.detection_index)
        return {image_path: frozenset(indices) for image_path, indices in indices_by_image.items()}

    def is_accepted(self, record: DetectionRecord) -> bool:
        """
        Whether a listed detection is kept for export.

        Parameters
        ----------
        record : DetectionRecord
            Detection to test.

        Returns
        -------
        bool
            False once rejected.
        """
        return self._table_model.is_accepted(record)

    def set_accepted(self, records: Sequence[DetectionRecord], is_accepted: bool) -> None:
        """
        Keep or reject detections of the listed results.

        Parameters
        ----------
        records : Sequence[DetectionRecord]
            Detections of the shown profile.
        is_accepted : bool
            True to keep them, False to reject them.

        Raises
        ------
        RuntimeError
            If no results are listed.
        """
        if records:
            self._update_rows(lambda: self._table_model.set_accepted(records, is_accepted))

    def save_listed_table(self, path: Path) -> int:
        """
        Save the listed detections as a CSV file, in display order.

        Parameters
        ----------
        path : Path
            CSV file to write, replaced if it exists.

        Returns
        -------
        int
            Number of detections written.

        Raises
        ------
        RuntimeError
            If no results are listed.
        OSError
            If the file cannot be written.
        """
        catalog: DetectionCatalog | None = self._table_model.catalog
        if catalog is None:
            raise RuntimeError("no results are listed")
        records: tuple[DetectionRecord, ...] = self.visible_records
        DetectionTableWriter().write(records, catalog, path)
        return len(records)

    def set_listed_accepted(self, is_accepted: bool) -> None:
        """
        Keep or reject every listed detection.

        Parameters
        ----------
        is_accepted : bool
            True to keep them, False to reject them.
        """
        if self._table_model.catalog is not None:
            self.set_accepted(self.visible_records, is_accepted)

    @property
    def class_thresholds(self) -> ClassThresholds:
        """
        Minimum confidence of each class.

        Returns
        -------
        ClassThresholds
            Thresholds hiding the detections below them.
        """
        return self._proxy_model.class_thresholds

    def set_class_thresholds(self, class_thresholds: ClassThresholds) -> None:
        """
        List only the detections reaching the minimum confidence of their class.

        Parameters
        ----------
        class_thresholds : ClassThresholds
            New thresholds.
        """
        self._update_rows(lambda: self._proxy_model.set_class_thresholds(class_thresholds))
        self._update_summary()

    def remove_images(self, image_paths: Sequence[Path]) -> None:
        """
        Stop listing images closed in the window.

        Parameters
        ----------
        image_paths : Sequence[Path]
            Closed images; images not listed are ignored.
        """
        self._update_rows(lambda: self._table_model.remove_images(image_paths))
        self._update_summary()

    @property
    def outdated_image_paths(self) -> tuple[Path, ...]:
        """
        Images detected with other classes than the current ones.

        Returns
        -------
        tuple[Path, ...]
            Outdated images in the order they were opened.
        """
        return self._table_model.outdated_image_paths

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
        table_filter: TableFilter = self._proxy_model.table_filter.with_condition(column, condition)
        self._update_rows(lambda: self._proxy_model.set_table_filter(table_filter))
        self._update_summary()

    def clear_filters(self) -> None:
        """
        Stop filtering every column.
        """
        self._update_rows(lambda: self._proxy_model.set_table_filter(TableFilter()))
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
        List newly opened images with their stored detections, or as not analyzed.

        Parameters
        ----------
        image_paths : Sequence[Path]
            Opened images; images already listed are left as they are.
        """
        self._update_rows(lambda: self._table_model.add_images(image_paths))
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
        self._update_rows(lambda: self._table_model.replace_image(image_path, records))
        self._update_summary()

    def set_prompt_changes(self, prompt_changes: Mapping[Path, PromptChange]) -> None:
        """
        Mark the images detected with other classes than the current ones.

        Parameters
        ----------
        prompt_changes : Mapping[Path, PromptChange]
            Change of every outdated image; other images are marked current.
        """
        self._update_rows(lambda: self._table_model.set_prompt_changes(prompt_changes))
        self._update_summary()

    def show_catalog(self, catalog: DetectionCatalog | None) -> None:
        """
        List the detections of one detector profile in place of the current ones.

        Parameters
        ----------
        catalog : DetectionCatalog | None
            Results to list; ``None`` lists every image as not analyzed.
        """
        self._update_rows(lambda: self._table_model.show_catalog(catalog))
        self._update_summary()

    def _build_table_view(self) -> None:
        self._table_view.setHorizontalHeader(self._header_view)
        self._table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table_view.addAction(self._toggle_action)
        self._table_view.setModel(self._proxy_model)
        self._table_view.setSortingEnabled(True)
        self._table_view.sortByColumn(-1, Qt.SortOrder.AscendingOrder)
        self._table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.verticalHeader().setVisible(False)
        self._header_view.setSortIndicatorShown(False)

    def _build_layout(self) -> None:
        button_row: QHBoxLayout = QHBoxLayout()
        button_row.addWidget(self._filter_button)
        button_row.addWidget(self._save_table_button)
        button_row.addStretch(1)
        button_row.addWidget(self._clear_filters_button)
        button_row.addWidget(self._update_outdated_button)
        button_row.addWidget(self._clear_button)
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._table_view, stretch=1)
        layout.addWidget(self._summary_label)
        layout.addLayout(button_row)

    def _connect_signals(self) -> None:
        self._header_view.filter_requested.connect(self._on_filter_requested)
        self._filter_menu.aboutToShow.connect(self._fill_filter_menu)
        self._clear_filters_button.clicked.connect(self.clear_filters)
        self._save_table_button.clicked.connect(self._choose_table_path)
        self._clear_button.clicked.connect(self.clear_requested)
        self._update_outdated_button.clicked.connect(self.update_outdated_requested)
        self._table_view.selectionModel().selectionChanged.connect(self._emit_selection)
        self._table_view.customContextMenuRequested.connect(self._show_context_menu)
        self._toggle_action.triggered.connect(self._toggle_selected)
        self._keep_listed_action.triggered.connect(lambda: self.set_listed_accepted(True))
        self._reject_listed_action.triggered.connect(lambda: self.set_listed_accepted(False))
        self._table_model.acceptance_changed.connect(self._on_acceptance_changed)
        self._proxy_model.rowsInserted.connect(self._update_summary)
        self._proxy_model.rowsRemoved.connect(self._update_summary)
        self._proxy_model.modelReset.connect(self._update_summary)

    def _fill_filter_menu(self) -> None:
        self._filter_menu.clear()
        for column in ResultColumn:
            condition: ColumnCondition | None = self.table_filter.condition_of(column)
            action: QAction = self._filter_menu.addAction(
                column.header if condition is None else f"{column.header}: {condition.description}"
            )
            action.setCheckable(True)
            action.setChecked(condition is not None)
            action.triggered.connect(partial(self.open_filter_popup, column))
        self._filter_menu.addSeparator()
        clear_action: QAction = self._filter_menu.addAction("Clear Filters")
        clear_action.setEnabled(not self.table_filter.is_empty)
        clear_action.triggered.connect(self.clear_filters)

    def _default_column_width(self, logical_index: int) -> int:
        is_filtered: bool = self.table_filter.condition_of(ResultColumn(logical_index)) is not None
        header_width: int = self._header_view.sectionSizeHint(logical_index) if is_filtered else 0
        return max(
            self._table_view.sizeHintForColumn(logical_index), header_width, self._header_view.minimumSectionSize()
        )

    def _on_acceptance_changed(self, image_path: Path) -> None:
        self._update_summary()
        self.acceptance_changed.emit(image_path)
        if not self._is_updating_rows:
            self.listing_changed.emit()

    def _toggle_selected(self) -> None:
        record: DetectionRecord | None = self.selected_record
        if record is not None:
            self.set_accepted((record,), not self.is_accepted(record))

    def _show_context_menu(self, position: QPoint) -> None:
        record: DetectionRecord | None = self.selected_record
        menu: QMenu = QMenu(self)
        if record is not None:
            keep_action: QAction = menu.addAction("Keep Detection")
            keep_action.setEnabled(not self.is_accepted(record))
            keep_action.triggered.connect(lambda: self.set_accepted((record,), True))
            reject_action: QAction = menu.addAction("Reject Detection")
            reject_action.setEnabled(self.is_accepted(record))
            reject_action.triggered.connect(lambda: self.set_accepted((record,), False))
            menu.addSeparator()
        listed_count: int = len(self.visible_records)
        self._keep_listed_action.setText(f"Keep All {listed_count} Listed")
        self._reject_listed_action.setText(f"Reject All {listed_count} Listed")
        is_listing_results: bool = self._table_model.catalog is not None and listed_count > 0
        self._keep_listed_action.setEnabled(is_listing_results)
        self._reject_listed_action.setEnabled(is_listing_results)
        menu.addAction(self._keep_listed_action)
        menu.addAction(self._reject_listed_action)
        menu.addSeparator()
        save_action: QAction = menu.addAction(f"Save {listed_count} Listed as CSV…")
        save_action.setEnabled(is_listing_results)
        save_action.triggered.connect(self._choose_table_path)
        menu.exec(self._table_view.viewport().mapToGlobal(position))

    def _choose_table_path(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Detection Table", str(self._table_path), f"CSV files (*{self.TABLE_FILE_SUFFIX})"
        )
        if not file_name:
            return
        path: Path = Path(file_name)
        if path.suffix.lower() != self.TABLE_FILE_SUFFIX:
            path = path.with_name(f"{path.name}{self.TABLE_FILE_SUFFIX}")
        self._table_path = path
        try:
            written_count: int = self.save_listed_table(path)
        except (RuntimeError, OSError) as error:
            self.message_posted.emit(f"Could not save the detection table: {error}")
            return
        self.message_posted.emit(f"Saved {written_count} detection{'' if written_count == 1 else 's'} to {path}.")

    def _on_filter_requested(self, logical_index: int, position: QPoint) -> None:
        self.open_filter_popup(ResultColumn(logical_index), position)

    def _update_summary(self) -> None:
        visible_count: int = len(self.visible_records)
        total_count: int = len(self._table_model.records)
        rejected_count: int = sum(1 for record in self._table_model.records if not self.is_accepted(record))
        rejected_note: str = f" · {rejected_count} rejected" if rejected_count else ""
        below_minimum_count: int = sum(
            1 for record in self._table_model.records if not self._proxy_model.is_above_minimum(record)
        )
        below_minimum_note: str = f" · {below_minimum_count} below class minimums" if below_minimum_count else ""
        not_analyzed_count: int = sum(
            1
            for row in self._table_model.rows
            if isinstance(row, ImageStatusRow) and row.state == AnalysisState.NOT_ANALYZED
        )
        not_analyzed_note: str = f" · {not_analyzed_count} not analyzed" if not_analyzed_count else ""
        outdated_count: int = len(self.outdated_image_paths)
        outdated_note: str = f" · {outdated_count} outdated" if outdated_count else ""
        filtered_headers: list[str] = [
            column.header for column in ResultColumn if self.table_filter.condition_of(column) is not None
        ]
        filter_note: str = f" · filtered by {', '.join(filtered_headers)}" if filtered_headers else ""
        self._summary_label.setText(
            f"{visible_count} / {total_count} detections{rejected_note}{below_minimum_note}{not_analyzed_note}"
            + f"{outdated_note}{filter_note}"
        )
        self._update_outdated_button.setVisible(bool(outdated_count))
        self._column_auto_fit.fit()
        self._clear_filters_button.setEnabled(bool(filtered_headers))
        self._save_table_button.setEnabled(self._table_model.catalog is not None and visible_count > 0)
        self._filter_button.setIcon(self._funnel_icons[bool(filtered_headers)])
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

    def _selected_row(self) -> ResultRow | None:
        selected_rows: list[int] = self._selected_proxy_rows()
        return self._proxy_model.row_at(selected_rows[0]) if selected_rows else None

    def _update_rows(self, update: Callable[[], None]) -> None:
        previous_row: ResultRow | None = self._selected_row()
        self._is_updating_rows = True
        update()
        is_selection_kept: bool = previous_row is None or self._select_silently(previous_row)
        self._is_updating_rows = False
        if not is_selection_kept:
            self.selection_cleared.emit()
        self.listing_changed.emit()

    def _select_silently(self, row: ResultRow) -> bool:
        selection_model: QItemSelectionModel = self._table_view.selectionModel()
        for proxy_row in range(self._proxy_model.rowCount()):
            if self._proxy_model.row_at(proxy_row) is row:
                selection_model.setCurrentIndex(
                    self._proxy_model.index(proxy_row, 0),
                    QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
                )
                return True
        selection_model.clearSelection()
        return False

    def _emit_selection(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        if self._is_updating_rows:
            return
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
