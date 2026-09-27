from collections.abc import Sequence
from functools import partial

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...analysis import ClassComparison, ClassStatistics, ConfidenceHistogram, ProfileComparison, ResultStatistics
from ...detection import DetectorProfile
from ...review import ClassThresholds
from ..class_palette import ClassPalette
from .comparison_column import ComparisonColumn
from .confidence_histogram_view import ConfidenceHistogramView
from .minimum_spin_box import MinimumSpinBox
from .statistics_column import StatisticsColumn


class StatisticsWindow(QDialog):
    """
    Statistics of the shown model over the open images, the minimum confidence of each class, and a comparison
    with another stored model.

    The class table counts the detections of each class, how many are rejected or below the minimum confidence of
    their class, and their mean and median confidence; its last column sets the minimum of the class, and the value
    above it the default of every other class. The histogram shows the confidences of the selected class, or of every
    class when none is selected, with the minimum marked. Choosing a model to compare with lists, per class, the
    detections both models found on the images they both detected, paired one to one by box overlap.

    The window is not modal and is refreshed by the main window while it is visible; refreshing keeps the selected
    class and never overwrites a minimum being edited.

    Signals
    -------
    thresholds_changed : Signal(ClassThresholds)
        The user changed the default or a class minimum.
    comparison_selected : Signal(DetectorProfile)
        The user chose a model to compare with.
    comparison_cleared : Signal()
        The user stopped comparing.
    """

    thresholds_changed: Signal = Signal(ClassThresholds)
    comparison_selected: Signal = Signal(DetectorProfile)
    comparison_cleared: Signal = Signal()

    WINDOW_TITLE = "Statistics"
    NO_COMPARISON_TEXT = "None"
    OTHER_CLASS_COLOR = QColor(140, 140, 140)

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
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setModal(False)
        self.resize(760, 640)
        self._palette: ClassPalette = palette
        self._statistics: ResultStatistics | None = None
        self._class_names: tuple[str, ...] = ()
        self._thresholds: ClassThresholds = ClassThresholds()
        self._listed_class_names: tuple[str, ...] = ()
        self._minimum_spins: dict[str, MinimumSpinBox] = {}
        self._comparison_profiles: tuple[DetectorProfile, ...] = ()

        self._summary_label: QLabel = QLabel()
        self._default_spin: QDoubleSpinBox = QDoubleSpinBox()
        self._default_spin.setRange(0.0, 1.0)
        self._default_spin.setSingleStep(MinimumSpinBox.STEP)
        self._default_spin.setDecimals(2)
        self._default_spin.setToolTip("Minimum confidence of every class set to Default in the table")
        self._class_table: QTableWidget = QTableWidget(0, len(StatisticsColumn))
        self._histogram_view: ConfidenceHistogramView = ConfidenceHistogramView()
        self._comparison_combo: QComboBox = QComboBox()
        self._comparison_label: QLabel = QLabel()
        self._comparison_label.setWordWrap(True)
        self._comparison_table: QTableWidget = QTableWidget(0, len(ComparisonColumn))

        self._build_tables()
        self._build_layout()
        self._default_spin.valueChanged.connect(self._on_default_changed)
        self._class_table.itemSelectionChanged.connect(self._update_histogram)
        self._comparison_combo.currentIndexChanged.connect(self._on_comparison_chosen)
        self.set_comparison_candidates((), None)
        self.show_statistics(None, "", (), ClassThresholds())

    @property
    def class_thresholds(self) -> ClassThresholds:
        """
        Minimums shown in the window.

        Returns
        -------
        ClassThresholds
            Default and per-class minimum confidences.
        """
        return self._thresholds

    @property
    def compared_profile(self) -> DetectorProfile | None:
        """
        Model chosen to compare with.

        Returns
        -------
        DetectorProfile | None
            ``None`` while not comparing.
        """
        index: int = self._comparison_combo.currentIndex()
        return self._comparison_profiles[index - 1] if 0 < index <= len(self._comparison_profiles) else None

    @property
    def selected_class_name(self) -> str | None:
        """
        Class whose confidences the histogram shows.

        Returns
        -------
        str | None
            ``None`` while no row is selected, when the histogram shows every class.
        """
        selected_rows: list[int] = sorted({index.row() for index in self._class_table.selectedIndexes()})
        if not selected_rows or selected_rows[0] >= len(self._listed_class_names):
            return None
        return self._listed_class_names[selected_rows[0]]

    @property
    def histogram(self) -> ConfidenceHistogram:
        """
        Histogram drawn now.

        Returns
        -------
        ConfidenceHistogram
            Confidences of the selected class or of every class.
        """
        return self._histogram_view.histogram

    def show_statistics(
        self,
        statistics: ResultStatistics | None,
        model_name: str,
        class_names: Sequence[str],
        thresholds: ClassThresholds,
    ) -> None:
        """
        Show the statistics of the shown model.

        Parameters
        ----------
        statistics : ResultStatistics | None
            Statistics to show; ``None`` while no model is shown.
        model_name : str
            Name of the shown model.
        class_names : Sequence[str]
            Current classes, deciding the colors.
        thresholds : ClassThresholds
            Minimums to show.
        """
        self._statistics = statistics
        self._class_names = tuple(class_names)
        self._thresholds = thresholds
        if statistics is None:
            self._summary_label.setText("Detect images to see statistics.")
        else:
            detection_count: int = sum(entry.detection_count for entry in statistics.classes)
            kept_count: int = sum(entry.kept_count for entry in statistics.classes)
            self._summary_label.setText(
                f"<b>{model_name}</b> · {statistics.detected_image_count} of {statistics.image_count} open images "
                + f"detected · {kept_count} of {detection_count} detections kept"
            )
        if not self._default_spin.hasFocus():
            self._default_spin.blockSignals(True)
            self._default_spin.setValue(thresholds.default_minimum)
            self._default_spin.blockSignals(False)
        entries: tuple[ClassStatistics, ...] = () if statistics is None else statistics.classes
        self._fill_class_table(entries)
        self._update_histogram()

    def set_comparison_candidates(
        self, profiles: Sequence[DetectorProfile], compared_profile: DetectorProfile | None
    ) -> None:
        """
        List the models that can be compared with the shown one.

        Parameters
        ----------
        profiles : Sequence[DetectorProfile]
            Stored profiles other than the shown one.
        compared_profile : DetectorProfile | None
            Profile to select; ``None``, or one not listed, selects no comparison.
        """
        self._comparison_profiles = tuple(profiles)
        self._comparison_combo.blockSignals(True)
        self._comparison_combo.clear()
        self._comparison_combo.addItem(self.NO_COMPARISON_TEXT)
        for profile in self._comparison_profiles:
            self._comparison_combo.addItem(f"{profile.model_name} ({profile.options_text})")
        selected_index: int = (
            self._comparison_profiles.index(compared_profile) + 1
            if compared_profile in self._comparison_profiles
            else 0
        )
        self._comparison_combo.setCurrentIndex(selected_index)
        self._comparison_combo.setEnabled(bool(self._comparison_profiles))
        self._comparison_combo.blockSignals(False)

    def show_comparison(self, comparison: ProfileComparison | None) -> None:
        """
        Show the per-class comparison with the chosen model.

        Parameters
        ----------
        comparison : ProfileComparison | None
            Comparison to show; ``None`` while not comparing.
        """
        compared_profile: DetectorProfile | None = self.compared_profile
        if comparison is None or compared_profile is None:
            self._comparison_label.setText(
                "Choose another stored model to compare its detections with the shown model."
                if self._comparison_profiles
                else "Detect with another model to compare it here."
            )
            self._comparison_table.setRowCount(0)
            return
        self._comparison_label.setText(
            f"{comparison.image_count} images detected by both · detections paired when their boxes overlap by an "
            + f"IoU of at least {comparison.iou_threshold:.2f} · every stored detection counts, rejected or not"
        )
        self._comparison_table.setRowCount(len(comparison.classes))
        for row, entry in enumerate(comparison.classes):
            for column in ComparisonColumn:
                item: QTableWidgetItem = QTableWidgetItem(self._comparison_text(entry, column))
                if column != ComparisonColumn.CLASS:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setIcon(self._class_swatch(entry.class_name))
                self._comparison_table.setItem(row, column.value, item)

    def _build_tables(self) -> None:
        for table, headers, tool_tips in (
            (
                self._class_table,
                [column.header for column in StatisticsColumn],
                [column.tool_tip for column in StatisticsColumn],
            ),
            (
                self._comparison_table,
                [column.header for column in ComparisonColumn],
                [column.tool_tip for column in ComparisonColumn],
            ),
        ):
            table.setHorizontalHeaderLabels(headers)
            for column_index, tool_tip in enumerate(tool_tips):
                header_item: QTableWidgetItem | None = table.horizontalHeaderItem(column_index)
                if header_item is not None:
                    header_item.setToolTip(tool_tip)
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            header: QHeaderView = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._class_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._class_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._comparison_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

    def _build_layout(self) -> None:
        form_layout: QFormLayout = QFormLayout()
        form_layout.addRow("Default minimum confidence", self._default_spin)
        comparison_group: QGroupBox = QGroupBox("Compare With")
        comparison_layout: QVBoxLayout = QVBoxLayout(comparison_group)
        comparison_layout.addWidget(self._comparison_combo)
        comparison_layout.addWidget(self._comparison_label)
        comparison_layout.addWidget(self._comparison_table, stretch=1)
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.addWidget(self._summary_label)
        layout.addLayout(form_layout)
        layout.addWidget(self._class_table, stretch=2)
        layout.addWidget(self._histogram_view, stretch=1)
        layout.addWidget(comparison_group, stretch=1)

    def _fill_class_table(self, entries: Sequence[ClassStatistics]) -> None:
        names: tuple[str, ...] = tuple(entry.class_name for entry in entries)
        if names != self._listed_class_names:
            selected_name: str | None = self.selected_class_name
            self._class_table.blockSignals(True)
            self._class_table.clearSelection()
            self._class_table.setRowCount(len(entries))
            self._minimum_spins = {}
            for row, class_name in enumerate(names):
                spin: MinimumSpinBox = MinimumSpinBox()
                spin.valueChanged.connect(partial(self._on_class_minimum_changed, class_name))
                self._class_table.setCellWidget(row, StatisticsColumn.MINIMUM.value, spin)
                self._minimum_spins[class_name] = spin
            self._listed_class_names = names
            if selected_name in names:
                self._class_table.selectRow(names.index(selected_name))
            self._class_table.blockSignals(False)
        for row, entry in enumerate(entries):
            for column in StatisticsColumn:
                if column == StatisticsColumn.MINIMUM:
                    continue
                item: QTableWidgetItem = QTableWidgetItem(self._statistics_text(entry, column))
                if column == StatisticsColumn.CLASS:
                    item.setIcon(self._class_swatch(entry.class_name))
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._class_table.setItem(row, column.value, item)
            spin = self._minimum_spins[entry.class_name]
            if not spin.hasFocus():
                spin.set_minimum_confidence(
                    self._thresholds.class_minimums.get(entry.class_name)
                    if self._thresholds.has_own_minimum(entry.class_name)
                    else None
                )

    def _update_histogram(self) -> None:
        selected_name: str | None = self.selected_class_name
        statistics: ResultStatistics | None = self._statistics
        if selected_name is None:
            confidences: tuple[float, ...] = () if statistics is None else statistics.confidences
            self._histogram_view.show_histogram(
                ConfidenceHistogram.of(confidences),
                self._thresholds.default_minimum,
                self.palette().color(QPalette.ColorRole.Highlight),
                "Confidence of every class",
            )
            return
        entry: ClassStatistics | None = None if statistics is None else statistics.class_named(selected_name)
        self._histogram_view.show_histogram(
            ConfidenceHistogram.of(() if entry is None else entry.confidences),
            self._thresholds.minimum_of(selected_name),
            self._class_color(selected_name),
            f"Confidence of {selected_name}",
        )

    def _on_default_changed(self, value: float) -> None:
        self._thresholds = self._thresholds.with_default_minimum(value)
        self._update_histogram()
        self.thresholds_changed.emit(self._thresholds)

    def _on_class_minimum_changed(self, class_name: str, value: float) -> None:
        self._thresholds = self._thresholds.with_class_minimum(
            class_name, self._minimum_spins[class_name].minimum_confidence
        )
        self._update_histogram()
        self.thresholds_changed.emit(self._thresholds)

    def _on_comparison_chosen(self) -> None:
        compared_profile: DetectorProfile | None = self.compared_profile
        if compared_profile is None:
            self.comparison_cleared.emit()
        else:
            self.comparison_selected.emit(compared_profile)

    def _class_color(self, class_name: str) -> QColor:
        if class_name in self._class_names:
            return self._palette.color_of(self._class_names.index(class_name))
        return self.OTHER_CLASS_COLOR

    def _class_swatch(self, class_name: str) -> QIcon:
        if class_name in self._class_names:
            return self._palette.swatch_of(self._class_names.index(class_name))
        swatch: QPixmap = QPixmap(ClassPalette.SWATCH_SIZE, ClassPalette.SWATCH_SIZE)
        swatch.fill(self.OTHER_CLASS_COLOR)
        return QIcon(swatch)

    @staticmethod
    def _statistics_text(entry: ClassStatistics, column: StatisticsColumn) -> str:
        match column:
            case StatisticsColumn.CLASS:
                return entry.class_name
            case StatisticsColumn.IMAGES:
                return str(entry.image_count)
            case StatisticsColumn.DETECTIONS:
                return str(entry.detection_count)
            case StatisticsColumn.REJECTED:
                return str(entry.rejected_count)
            case StatisticsColumn.BELOW_MINIMUM:
                return str(entry.below_minimum_count)
            case StatisticsColumn.KEPT:
                return str(entry.kept_count)
            case StatisticsColumn.MEAN:
                return "" if entry.mean_confidence is None else f"{entry.mean_confidence:.3f}"
            case StatisticsColumn.MEDIAN:
                return "" if entry.median_confidence is None else f"{entry.median_confidence:.3f}"
            case StatisticsColumn.MINIMUM:
                return ""

    @staticmethod
    def _comparison_text(entry: ClassComparison, column: ComparisonColumn) -> str:
        match column:
            case ComparisonColumn.CLASS:
                return entry.class_name
            case ComparisonColumn.SHOWN:
                return str(entry.baseline_count)
            case ComparisonColumn.COMPARED:
                return str(entry.candidate_count)
            case ComparisonColumn.MATCHED:
                return str(entry.matched_count)
            case ComparisonColumn.SHOWN_ONLY:
                return str(entry.baseline_only_count)
            case ComparisonColumn.COMPARED_ONLY:
                return str(entry.candidate_only_count)
