from collections.abc import Sequence

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...detection import DetectorProfile, ProfileSummary
from .column_auto_fit import ColumnAutoFit
from .outdated_icon import OutdatedIcon
from .profile_column import ProfileColumn


class ProfilePanel(QWidget):
    """
    Table of the models whose results are stored, one row per detector profile.

    The selected row is the profile whose results the window shows; selecting another row switches to its results
    without detecting again. ``Outdated`` counts the images of a profile detected with other classes, phrases or
    reference boxes than the current ones. Columns fit their contents until the user drags a column edge. The selected profile can be removed with the Remove button, the Delete key or the
    right-click menu.

    Signals
    -------
    profile_selected : Signal(DetectorProfile)
        The user selected the row of a profile.
    removal_requested : Signal(DetectorProfile)
        The user asked to forget the results of a profile.
    """

    profile_selected: Signal = Signal(DetectorProfile)
    removal_requested: Signal = Signal(DetectorProfile)

    TITLE = "Models"
    EMPTY_HINT = "Detect to compare models here."

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._profiles: list[DetectorProfile] = []
        self._tree: QTreeWidget = QTreeWidget()
        self._hint_label: QLabel = QLabel(self.EMPTY_HINT)
        self._remove_button: QPushButton = QPushButton("Remove")
        self._remove_button.setToolTip("Forget the results of the selected model")
        self._remove_action: QAction = QAction("Remove Results", self)
        self._remove_action.setShortcut(QKeySequence.StandardKey.Delete)
        self._remove_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._column_auto_fit: ColumnAutoFit = ColumnAutoFit(
            self._tree.header(),
            lambda column: max(self._tree.sizeHintForColumn(column), self._tree.header().sectionSizeHint(column)),
        )
        self._build_tree()
        self._build_layout()
        self._connect_signals()
        self._update_controls()

    @property
    def profiles(self) -> tuple[DetectorProfile, ...]:
        """
        Listed profiles.

        Returns
        -------
        tuple[DetectorProfile, ...]
            Profiles in row order.
        """
        return tuple(self._profiles)

    @property
    def selected_profile(self) -> DetectorProfile | None:
        """
        Profile of the selected row.

        Returns
        -------
        DetectorProfile | None
            ``None`` while no row is selected.
        """
        item: QTreeWidgetItem | None = self._tree.currentItem()
        if item is None or not item.isSelected():
            return None
        return self._profiles[self._tree.indexOfTopLevelItem(item)]

    def select_profile(self, profile: DetectorProfile) -> None:
        """
        Select the row of a profile as the user would, reporting it through ``profile_selected``.

        Parameters
        ----------
        profile : DetectorProfile
            Listed profile to select.

        Raises
        ------
        KeyError
            If ``profile`` is not listed.
        """
        if profile not in self._profiles:
            raise KeyError(f"{profile.model_name} ({profile.options_text}) is not listed")
        item: QTreeWidgetItem | None = self._tree.topLevelItem(self._profiles.index(profile))
        if item is not None:
            self._tree.setCurrentItem(item)

    def set_summaries(self, summaries: Sequence[ProfileSummary], shown_profile: DetectorProfile | None) -> None:
        """
        List the stored profiles and select the one being shown.

        Parameters
        ----------
        summaries : Sequence[ProfileSummary]
            One summary per stored profile, in row order.
        shown_profile : DetectorProfile | None
            Profile to select; ``None`` selects no row.

        Raises
        ------
        KeyError
            If ``shown_profile`` is not among ``summaries``.
        """
        profiles: list[DetectorProfile] = [summary.profile for summary in summaries]
        if shown_profile is not None and shown_profile not in profiles:
            raise KeyError(f"{shown_profile.model_name} ({shown_profile.options_text}) is not listed")
        self._tree.blockSignals(True)
        self._tree.clear()
        self._profiles = profiles
        items: list[QTreeWidgetItem] = [self._item_of(summary) for summary in summaries]
        self._tree.addTopLevelItems(items)
        if shown_profile is not None:
            self._tree.setCurrentItem(items[profiles.index(shown_profile)])
        self._tree.blockSignals(False)
        self._column_auto_fit.fit()
        self._update_controls()

    def _build_tree(self) -> None:
        self._tree.setColumnCount(len(ProfileColumn))
        self._tree.setHeaderLabels([column.header for column in ProfileColumn])
        self._tree.setRootIsDecorated(False)
        self._tree.setUniformRowHeights(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.addAction(self._remove_action)

    def _build_layout(self) -> None:
        title_label: QLabel = QLabel(self.TITLE)
        title_font: QFont = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_row: QHBoxLayout = QHBoxLayout()
        header_row.addWidget(title_label)
        header_row.addWidget(self._hint_label, stretch=1)
        header_row.addWidget(self._remove_button)
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header_row)
        layout.addWidget(self._tree, stretch=1)

    def _connect_signals(self) -> None:
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._remove_button.clicked.connect(self._request_removal)
        self._remove_action.triggered.connect(self._request_removal)

    def _item_of(self, summary: ProfileSummary) -> QTreeWidgetItem:
        item: QTreeWidgetItem = QTreeWidgetItem(
            [
                summary.profile.model_name,
                summary.profile.options_text,
                str(summary.image_count),
                str(summary.outdated_image_count) if summary.outdated_image_count else "",
                str(summary.detection_count),
            ]
        )
        item.setToolTip(ProfileColumn.MODEL.value, f"{summary.profile.backend.value}: {summary.profile.weights_path}")
        if summary.outdated_image_count:
            item.setIcon(ProfileColumn.OUTDATED.value, OutdatedIcon().to_icon())
            item.setToolTip(
                ProfileColumn.OUTDATED.value,
                f"{summary.outdated_image_count} of {summary.image_count} images were detected with other classes",
            )
        for column in ProfileColumn:
            if column.is_numeric:
                item.setTextAlignment(column.value, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item

    def _on_selection_changed(self) -> None:
        self._update_controls()
        profile: DetectorProfile | None = self.selected_profile
        if profile is not None:
            self.profile_selected.emit(profile)

    def _request_removal(self) -> None:
        profile: DetectorProfile | None = self.selected_profile
        if profile is not None:
            self.removal_requested.emit(profile)

    def _show_context_menu(self, position: QPoint) -> None:
        if self._tree.itemAt(position) is None:
            return
        menu: QMenu = QMenu(self)
        menu.addAction(self._remove_action)
        menu.exec(self._tree.viewport().mapToGlobal(position))

    def _update_controls(self) -> None:
        is_selected: bool = self.selected_profile is not None
        self._remove_button.setEnabled(is_selected)
        self._remove_action.setEnabled(is_selected)
        self._hint_label.setVisible(not self._profiles)
