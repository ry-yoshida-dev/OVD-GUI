from PySide6.QtCore import QModelIndex, QPersistentModelIndex
from PySide6.QtWidgets import QLineEdit, QStyledItemDelegate, QStyleOptionViewItem, QWidget


class PlaceholderItemDelegate(QStyledItemDelegate):
    """
    Item delegate whose line edit shows a hint while it is empty, e.g. while naming a row that was just added.

    Attributes
    ----------
    placeholder_text : str
        Hint shown by the next editor; empty for no hint.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self.placeholder_text: str = ""

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex
    ) -> QWidget:
        editor: QWidget = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setPlaceholderText(self.placeholder_text)
        return editor
