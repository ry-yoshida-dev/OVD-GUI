from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from .value_condition import ValueCondition


class ValueChecklist(QWidget):
    """
    Editor of a ``ValueCondition``: a searchable list of the values of a text column, each with a check box.

    ``Select all`` checks or unchecks the values matching the search. Checking every value means no condition.
    """

    MINIMUM_LIST_HEIGHT = 200

    def __init__(self, texts: Sequence[str], condition: ValueCondition | None, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        texts : Sequence[str]
            Values to offer, in list order; the empty string stands for blank cells.
        condition : ValueCondition | None
            Condition in effect, whose values start checked; ``None`` checks every value.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._search_edit: QLineEdit = QLineEdit()
        self._search_edit.setPlaceholderText("Search")
        self._search_edit.setClearButtonEnabled(True)
        self._select_all_check: QCheckBox = QCheckBox("Select all")
        self._select_all_check.setTristate(True)
        self._list_widget: QListWidget = QListWidget()
        self._list_widget.setMinimumHeight(self.MINIMUM_LIST_HEIGHT)
        for text in texts:
            item: QListWidgetItem = QListWidgetItem(text or ValueCondition.BLANK_LABEL, self._list_widget)
            item.setData(Qt.ItemDataRole.UserRole, text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            is_checked: bool = condition is None or condition.accepts(text)
            item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._search_edit)
        layout.addWidget(self._select_all_check)
        layout.addWidget(self._list_widget, stretch=1)

        self._search_edit.textChanged.connect(self._apply_search)
        self._select_all_check.clicked.connect(self._on_select_all_clicked)
        self._list_widget.itemChanged.connect(self._refresh_select_all)
        self._refresh_select_all()

    @property
    def condition(self) -> ValueCondition | None:
        """
        Condition chosen by the check boxes.

        Returns
        -------
        ValueCondition | None
            Checked values, or ``None`` when every value is checked.
        """
        items: list[QListWidgetItem] = self._items()
        checked_texts: frozenset[str] = frozenset(
            self._text_of(item) for item in items if item.checkState() == Qt.CheckState.Checked
        )
        if len(checked_texts) == len(items):
            return None
        return ValueCondition(checked_texts)

    def set_search_text(self, text: str) -> None:
        """
        Show only the values containing some text.

        Parameters
        ----------
        text : str
            Case-insensitive text to search for; blank shows every value.
        """
        self._search_edit.setText(text)

    def set_matching_checked(self, is_checked: bool) -> None:
        """
        Check or uncheck every value matching the search.

        Parameters
        ----------
        is_checked : bool
            Whether to check the values.
        """
        state: Qt.CheckState = Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked
        for item in self._visible_items():
            item.setCheckState(state)

    def set_text_checked(self, text: str, is_checked: bool) -> None:
        """
        Check or uncheck one value.

        Parameters
        ----------
        text : str
            Value to change.
        is_checked : bool
            Whether to check it.

        Raises
        ------
        KeyError
            If ``text`` is not offered.
        """
        for item in self._items():
            if self._text_of(item) == text:
                item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
                return
        raise KeyError(text)

    def _apply_search(self, text: str) -> None:
        needle: str = text.strip().casefold()
        for item in self._items():
            item.setHidden(needle not in item.text().casefold())
        self._refresh_select_all()

    def _on_select_all_clicked(self) -> None:
        self.set_matching_checked(self._select_all_check.checkState() != Qt.CheckState.Unchecked)

    def _refresh_select_all(self) -> None:
        visible_items: list[QListWidgetItem] = self._visible_items()
        checked_count: int = sum(1 for item in visible_items if item.checkState() == Qt.CheckState.Checked)
        state: Qt.CheckState = Qt.CheckState.PartiallyChecked
        if checked_count == 0:
            state = Qt.CheckState.Unchecked
        elif checked_count == len(visible_items):
            state = Qt.CheckState.Checked
        self._select_all_check.blockSignals(True)
        self._select_all_check.setCheckState(state)
        self._select_all_check.blockSignals(False)

    def _items(self) -> list[QListWidgetItem]:
        return [self._list_widget.item(row) for row in range(self._list_widget.count())]

    def _visible_items(self) -> list[QListWidgetItem]:
        return [item for item in self._items() if not item.isHidden()]

    @staticmethod
    def _text_of(item: QListWidgetItem) -> str:
        text: object = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(text, str):
            raise TypeError(f"list item must hold its value as str. got {type(text).__name__}")
        return text
