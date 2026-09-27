from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialogButtonBox, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from .column_condition import ColumnCondition
from .range_editor import RangeEditor
from .result_column import ResultColumn
from .value_checklist import ValueChecklist


class ColumnFilterPopup(QFrame):
    """
    Popup editing the condition of one column of the detection table.

    Applying reports the edited condition through ``condition_applied``; clearing reports ``None``. The popup closes
    itself afterwards, and when clicking outside it.

    Signals
    -------
    condition_applied : Signal(ResultColumn, object)
        The column and its new ``ColumnCondition``, or ``None`` to stop filtering it.
    """

    condition_applied: Signal = Signal(ResultColumn, object)

    def __init__(
        self, column: ResultColumn, editor: ValueChecklist | RangeEditor, parent: QWidget | None = None
    ) -> None:
        """
        Parameters
        ----------
        column : ResultColumn
            Column to filter.
        editor : ValueChecklist | RangeEditor
            Editor of the condition, a value checklist for a text column and a range for a numeric one.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent, Qt.WindowType.Popup)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._column: ResultColumn = column
        self._editor: ValueChecklist | RangeEditor = editor

        title_label: QLabel = QLabel(f"Filter {column.header}")
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        button_box: QDialogButtonBox = QDialogButtonBox()
        self._clear_button: QPushButton = button_box.addButton("Clear Filter", QDialogButtonBox.ButtonRole.ResetRole)
        self._apply_button: QPushButton = button_box.addButton(QDialogButtonBox.StandardButton.Apply)
        self._apply_button.setDefault(True)
        cancel_button: QPushButton = button_box.addButton(QDialogButtonBox.StandardButton.Cancel)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.addWidget(title_label)
        layout.addWidget(editor, stretch=1)
        layout.addWidget(button_box)

        self._apply_button.clicked.connect(self.apply)
        self._clear_button.clicked.connect(self.clear)
        cancel_button.clicked.connect(self.close)

    @property
    def column(self) -> ResultColumn:
        """
        Filtered column.

        Returns
        -------
        ResultColumn
            Column whose condition is edited.
        """
        return self._column

    @property
    def editor(self) -> ValueChecklist | RangeEditor:
        """
        Editor of the condition.

        Returns
        -------
        ValueChecklist | RangeEditor
            Value checklist or range editor shown in the popup.
        """
        return self._editor

    def apply(self) -> None:
        """
        Report the edited condition and close.
        """
        condition: ColumnCondition | None = self._editor.condition
        self.condition_applied.emit(self._column, condition)
        self.close()

    def clear(self) -> None:
        """
        Report that the column is no longer filtered and close.
        """
        self.condition_applied.emit(self._column, None)
        self.close()
