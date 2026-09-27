from collections.abc import Collection

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QPalette
from PySide6.QtWidgets import QMenu, QToolButton, QWidget

from .funnel_icon import FunnelIcon


class ClassFilterButton(QToolButton):
    """
    Funnel button choosing which classes the detection table lists.

    Its menu checks any number of classes; checking none, or ``All classes``, lists every class. The funnel is
    filled and the button names the chosen classes while a filter is in effect.

    Signals
    -------
    selection_changed : Signal()
        The chosen classes changed.
    """

    selection_changed: Signal = Signal()

    ALL_CLASSES_LABEL = "All classes"
    MAXIMUM_NAMED_CLASSES = 2

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._class_names: tuple[str, ...] = ()
        self._selected_class_names: frozenset[str] = frozenset()
        self._menu: QMenu = QMenu(self)
        self._menu.aboutToShow.connect(self._populate_menu)
        self._menu.triggered.connect(self._on_action_triggered)
        self.setMenu(self._menu)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setToolTip("Only detections of the checked classes")
        self._refresh_appearance()

    @property
    def class_names(self) -> tuple[str, ...]:
        """
        Classes offered in the menu.

        Returns
        -------
        tuple[str, ...]
            Class names in menu order.
        """
        return self._class_names

    @property
    def selected_class_names(self) -> frozenset[str]:
        """
        Chosen classes.

        Returns
        -------
        frozenset[str]
            Checked classes; empty when every class is listed.
        """
        return self._selected_class_names

    def set_class_names(self, class_names: Collection[str]) -> None:
        """
        Offer classes in the menu, keeping the chosen ones offered even when no longer detected.

        Parameters
        ----------
        class_names : Collection[str]
            Detected class names.
        """
        self._class_names = tuple(sorted({*class_names, *self._selected_class_names}))

    def set_selected_class_names(self, class_names: Collection[str]) -> None:
        """
        Choose the listed classes.

        Parameters
        ----------
        class_names : Collection[str]
            Classes to list; empty lists every class.

        Raises
        ------
        KeyError
            If a class is not offered.
        """
        unknown_class_names: set[str] = set(class_names) - set(self._class_names)
        if unknown_class_names:
            raise KeyError(", ".join(sorted(unknown_class_names)))
        selected_class_names: frozenset[str] = frozenset(class_names)
        if selected_class_names == self._selected_class_names:
            return
        self._selected_class_names = selected_class_names
        self._refresh_appearance()
        self.selection_changed.emit()

    def _populate_menu(self) -> None:
        self._menu.clear()
        all_classes_action: QAction = self._menu.addAction(self.ALL_CLASSES_LABEL)
        all_classes_action.setCheckable(True)
        all_classes_action.setChecked(not self._selected_class_names)
        if not self._class_names:
            return
        self._menu.addSeparator()
        for class_name in self._class_names:
            class_action: QAction = self._menu.addAction(class_name)
            class_action.setCheckable(True)
            class_action.setChecked(class_name in self._selected_class_names)
            class_action.setData(class_name)

    def _on_action_triggered(self, action: QAction) -> None:
        class_name: object = action.data()
        if not isinstance(class_name, str):
            self.set_selected_class_names(())
        elif action.isChecked():
            self.set_selected_class_names(self._selected_class_names | {class_name})
        else:
            self.set_selected_class_names(self._selected_class_names - {class_name})

    def _refresh_appearance(self) -> None:
        is_filtered: bool = bool(self._selected_class_names)
        self.setIcon(FunnelIcon(self.palette().color(QPalette.ColorRole.ButtonText), is_filtered).to_icon())
        self.setText(self._summary_text())

    def _summary_text(self) -> str:
        selected_names: list[str] = sorted(self._selected_class_names)
        if not selected_names:
            return self.ALL_CLASSES_LABEL
        if len(selected_names) <= self.MAXIMUM_NAMED_CLASSES:
            return ", ".join(selected_names)
        return f"{len(selected_names)} classes"
