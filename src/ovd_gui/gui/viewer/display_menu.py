from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QWidget

from .display_options import DisplayOptions


class DisplayMenu(QMenu):
    """
    Menu choosing how detection boxes are drawn: labels, confidences, rejected detections, the compared model, line
    width and fill.

    Signals
    -------
    options_changed : Signal(DisplayOptions)
        The user changed an option.
    """

    options_changed: Signal = Signal(DisplayOptions)

    TITLE = "View"
    LINE_WIDTHS: tuple[int, ...] = (1, 2, 3, 4, 6)
    FILL_OPACITIES: tuple[int, ...] = (0, 15, 30, 50)

    def __init__(self, options: DisplayOptions, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        options : DisplayOptions
            Options shown checked at first.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(self.TITLE, parent)
        self._options: DisplayOptions = options
        self._label_action: QAction = self._add_toggle("Show Labels", options.is_label_shown)
        self._confidence_action: QAction = self._add_toggle("Show Confidence in Labels", options.is_confidence_shown)
        self._rejected_action: QAction = self._add_toggle("Show Rejected Detections", options.is_rejected_shown)
        self._comparison_action: QAction = self._add_toggle("Show Compared Model", options.is_comparison_shown)
        self._comparison_action.setToolTip("Draw the detections of the model chosen in Statistics › Compare, dotted")
        self.addSeparator()
        self._line_width_actions: dict[int, QAction] = self._add_choices(
            "Line Width", {width: f"{width} px" for width in self.LINE_WIDTHS}, options.line_width
        )
        self._fill_actions: dict[int, QAction] = self._add_choices(
            "Fill",
            {opacity: "None" if opacity == 0 else f"{opacity}%" for opacity in self.FILL_OPACITIES},
            options.fill_opacity,
        )
        self._confidence_action.setEnabled(options.is_label_shown)

    @property
    def options(self) -> DisplayOptions:
        """
        Options chosen in the menu.

        Returns
        -------
        DisplayOptions
            Current options.
        """
        return self._options

    def set_comparison_available(self, is_available: bool) -> None:
        """
        Enable the option drawing the compared model while one is chosen.

        Parameters
        ----------
        is_available : bool
            Whether a model is being compared.
        """
        self._comparison_action.setEnabled(is_available)

    def _add_toggle(self, text: str, is_checked: bool) -> QAction:
        action: QAction = self.addAction(text)
        action.setCheckable(True)
        action.setChecked(is_checked)
        action.toggled.connect(self._on_changed)
        return action

    def _add_choices(self, title: str, choices: dict[int, str], chosen: int) -> dict[int, QAction]:
        submenu: QMenu = self.addMenu(title)
        group: QActionGroup = QActionGroup(submenu)
        group.setExclusive(True)
        actions: dict[int, QAction] = {}
        for value, text in choices.items():
            action: QAction = submenu.addAction(text)
            action.setCheckable(True)
            action.setChecked(value == chosen)
            group.addAction(action)
            action.triggered.connect(self._on_changed)
            actions[value] = action
        return actions

    def _on_changed(self) -> None:
        self._confidence_action.setEnabled(self._label_action.isChecked())
        self._options = replace(
            self._options,
            is_label_shown=self._label_action.isChecked(),
            is_confidence_shown=self._confidence_action.isChecked(),
            is_rejected_shown=self._rejected_action.isChecked(),
            is_comparison_shown=self._comparison_action.isChecked(),
            line_width=self._checked_value(self._line_width_actions, self._options.line_width),
            fill_opacity=self._checked_value(self._fill_actions, self._options.fill_opacity),
        )
        self.options_changed.emit(self._options)

    @staticmethod
    def _checked_value(actions: dict[int, QAction], fallback: int) -> int:
        return next((value for value, action in actions.items() if action.isChecked()), fallback)
