from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsSimpleTextItem


class DetectionLabelItem(QGraphicsRectItem):
    """
    Text label on a filled background whose size does not change with zoom.
    """

    def __init__(self, text: str, background: QColor, foreground: QColor, parent: QGraphicsItem) -> None:
        """
        Parameters
        ----------
        text : str
            Label text.
        background : QColor
            Fill color behind the text.
        foreground : QColor
            Text color.
        parent : QGraphicsItem
            Item the label is attached to.
        """
        super().__init__(parent)
        text_item: QGraphicsSimpleTextItem = QGraphicsSimpleTextItem(text, self)
        font: QFont = text_item.font()
        font.setBold(True)
        text_item.setFont(font)
        text_item.setBrush(QBrush(foreground))
        self.setRect(text_item.boundingRect())
        self.setBrush(QBrush(background))
        self.setPen(Qt.PenStyle.NoPen)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
