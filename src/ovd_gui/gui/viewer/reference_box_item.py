from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsRectItem

from ...detection import ReferenceBox
from ..class_palette import ClassPalette
from .detection_label_item import DetectionLabelItem


class ReferenceBoxItem(QGraphicsRectItem):
    """
    Dashed outline of a reference box with its class label.
    """

    PEN_WIDTH = 2
    LABEL_PREFIX = "ref"

    def __init__(self, box: ReferenceBox, color: QColor) -> None:
        """
        Parameters
        ----------
        box : ReferenceBox
            Reference box in image pixel coordinates.
        color : QColor
            Color of the box's class.
        """
        super().__init__(QRectF(box.left, box.top, box.right - box.left, box.bottom - box.top))
        pen: QPen = QPen(color)
        pen.setCosmetic(True)
        pen.setWidth(self.PEN_WIDTH)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setZValue(2.0)
        label: DetectionLabelItem = DetectionLabelItem(
            text=f"{self.LABEL_PREFIX}: {box.class_name}",
            background=color,
            foreground=ClassPalette.text_color_on(color),
            parent=self,
        )
        label.setPos(box.left, box.top)
