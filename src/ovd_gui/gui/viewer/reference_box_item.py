from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem

from ...detection import ReferenceBox
from ..class_palette import ClassPalette
from .detection_label_item import DetectionLabelItem


class ReferenceBoxItem(QGraphicsRectItem):
    """
    Dashed outline of a reference box with its class label, and round corner handles while it is editable.
    """

    PEN_WIDTH = 2
    LABEL_PREFIX = "ref"
    HANDLE_RADIUS = 5.0
    HANDLE_FILL = QColor("#ffffff")

    def __init__(self, box: ReferenceBox, color: QColor, is_editable: bool = False) -> None:
        """
        Parameters
        ----------
        box : ReferenceBox
            Reference box in image pixel coordinates.
        color : QColor
            Color of the box's class.
        is_editable : bool, optional
            Whether round handles mark the corners that resize the box.
        """
        super().__init__()
        pen: QPen = QPen(color)
        pen.setCosmetic(True)
        pen.setWidth(self.PEN_WIDTH)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setZValue(2.0)
        self._label: DetectionLabelItem = DetectionLabelItem(
            text=f"{self.LABEL_PREFIX}: {box.class_name}",
            background=color,
            foreground=ClassPalette.text_color_on(color),
            parent=self,
        )
        self._handles: list[QGraphicsEllipseItem] = (
            [self._create_handle(color) for _ in range(4)] if is_editable else []
        )
        self.set_rectangle(QRectF(QPointF(box.left, box.top), QPointF(box.right, box.bottom)))

    @property
    def corners(self) -> tuple[QPointF, QPointF, QPointF, QPointF]:
        """
        Corners of the box in scene coordinates.

        Returns
        -------
        tuple[QPointF, QPointF, QPointF, QPointF]
            Top-left, top-right, bottom-right and bottom-left corners.
        """
        rectangle: QRectF = self.rect()
        return (rectangle.topLeft(), rectangle.topRight(), rectangle.bottomRight(), rectangle.bottomLeft())

    def set_rectangle(self, rectangle: QRectF) -> None:
        """
        Move the outline, label and handles to a new rectangle.

        Parameters
        ----------
        rectangle : QRectF
            Box in image pixel coordinates.
        """
        self.setRect(rectangle)
        self._label.setPos(rectangle.topLeft())
        for handle, corner in zip(self._handles, self.corners, strict=False):
            handle.setPos(corner)

    def _create_handle(self, color: QColor) -> QGraphicsEllipseItem:
        radius: float = self.HANDLE_RADIUS
        handle: QGraphicsEllipseItem = QGraphicsEllipseItem(-radius, -radius, 2.0 * radius, 2.0 * radius, self)
        handle_pen: QPen = QPen(color)
        handle_pen.setWidthF(1.5)
        handle.setPen(handle_pen)
        handle.setBrush(QBrush(self.HANDLE_FILL))
        handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        return handle
