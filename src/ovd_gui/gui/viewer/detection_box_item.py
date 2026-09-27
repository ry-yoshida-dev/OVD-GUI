from open_vocabulary_detector import Detection
from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsRectItem

from ..class_palette import ClassPalette
from .box_style import BoxStyle
from .detection_label_item import DetectionLabelItem
from .display_options import DisplayOptions


class DetectionBoxItem(QGraphicsRectItem):
    """
    Bounding box of one detection with its class and confidence label.

    Kept boxes are solid and may be filled, rejected ones dashed and faded, and those of the compared model dotted
    with their label under the box, so both models can be told apart where they overlap.
    """

    HIGHLIGHT_EXTRA_WIDTH = 3
    COMPARED_Z_VALUE = -0.5

    def __init__(
        self,
        detection: Detection,
        color: QColor,
        style: BoxStyle,
        options: DisplayOptions,
        label_prefix: str = "",
    ) -> None:
        """
        Parameters
        ----------
        detection : Detection
            Detection to draw, in image pixel coordinates.
        color : QColor
            Color of the detection's class.
        style : BoxStyle
            Role of the box.
        options : DisplayOptions
            Line width, fill and label content.
        label_prefix : str, optional
            Text put before the class name, e.g. the name of the compared model.
        """
        x_min, y_min, x_max, y_max = (float(value) for value in detection.box.value.tolist())
        super().__init__(QRectF(x_min, y_min, x_max - x_min, y_max - y_min))
        self._color: QColor = color
        self._style: BoxStyle = style
        self._line_width: int = options.line_width
        if style == BoxStyle.KEPT and options.fill_opacity:
            fill: QColor = QColor(color)
            fill.setAlphaF(options.fill_opacity / 100.0)
            self.setBrush(QBrush(fill))
        if options.is_label_shown:
            label: DetectionLabelItem = DetectionLabelItem(
                text=self._label_text(detection, options, label_prefix),
                background=color,
                foreground=ClassPalette.text_color_on(color),
                parent=self,
            )
            label.setPos(x_min, y_max if style == BoxStyle.COMPARED else y_min)
        self.set_highlighted(False)

    @property
    def style(self) -> BoxStyle:
        """
        Role of the box.

        Returns
        -------
        BoxStyle
            Style given at construction.
        """
        return self._style

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
        pen.setStyle(self._style.pen_style)
        pen.setWidth(self._line_width + (self.HIGHLIGHT_EXTRA_WIDTH if is_highlighted else 0))
        self.setPen(pen)
        base_z_value: float = self.COMPARED_Z_VALUE if self._style == BoxStyle.COMPARED else 0.0
        self.setZValue(1.0 if is_highlighted else base_z_value)
        self.setOpacity(1.0 if is_highlighted else self._style.opacity)

    @staticmethod
    def _label_text(detection: Detection, options: DisplayOptions, label_prefix: str) -> str:
        confidence_text: str = f" {detection.confidence:.2f}" if options.is_confidence_shown else ""
        prefix_text: str = f"{label_prefix}: " if label_prefix else ""
        return f"{prefix_text}{detection.class_name}{confidence_text}"
