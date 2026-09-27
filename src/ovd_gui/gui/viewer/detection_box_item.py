from open_vocabulary_detector import Detection
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsRectItem

from ..class_palette import ClassPalette
from .detection_label_item import DetectionLabelItem


class DetectionBoxItem(QGraphicsRectItem):
    """
    Bounding box of one detection with its class and confidence label.
    """

    NORMAL_PEN_WIDTH = 2
    HIGHLIGHTED_PEN_WIDTH = 5

    def __init__(self, detection: Detection, color: QColor) -> None:
        """
        Parameters
        ----------
        detection : Detection
            Detection to draw, in image pixel coordinates.
        color : QColor
            Color of the detection's class.
        """
        x_min, y_min, x_max, y_max = (float(value) for value in detection.box.value.tolist())
        super().__init__(QRectF(x_min, y_min, x_max - x_min, y_max - y_min))
        self._color: QColor = color
        self._label: DetectionLabelItem = DetectionLabelItem(
            text=f"{detection.class_name} {detection.confidence:.2f}",
            background=color,
            foreground=ClassPalette.text_color_on(color),
            parent=self,
        )
        self._label.setPos(x_min, y_min)
        self.set_highlighted(False)

    def set_highlighted(self, is_highlighted: bool) -> None:
        """
        Emphasize or restore the box outline.

        Parameters
        ----------
        is_highlighted : bool
            Whether the box is the selected detection.
        """
        pen: QPen = QPen(self._color)
        pen.setCosmetic(True)
        pen.setWidth(self.HIGHLIGHTED_PEN_WIDTH if is_highlighted else self.NORMAL_PEN_WIDTH)
        self.setPen(pen)
        self.setZValue(1.0 if is_highlighted else 0.0)
