from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


class TrashIcon:
    """
    Trash can icon drawn in a given color, for remove actions.
    """

    SIZE = 16
    PIXEL_RATIO = 3.0

    def __init__(self, color: QColor) -> None:
        """
        Parameters
        ----------
        color : QColor
            Stroke color, normally the button text color of the palette.
        """
        self._color: QColor = QColor(color)

    def to_icon(self) -> QIcon:
        """
        Render the trash can.

        Returns
        -------
        QIcon
            Icon of ``SIZE`` logical pixels drawn at a high pixel ratio.
        """
        pixmap: QPixmap = QPixmap(round(self.SIZE * self.PIXEL_RATIO), round(self.SIZE * self.PIXEL_RATIO))
        pixmap.setDevicePixelRatio(self.PIXEL_RATIO)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter: QPainter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen: QPen = QPen(self._color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawLine(QPointF(2.5, 4.0), QPointF(13.5, 4.0))
        handle: QPainterPath = QPainterPath(QPointF(6.0, 4.0))
        handle.lineTo(6.0, 2.5)
        handle.lineTo(10.0, 2.5)
        handle.lineTo(10.0, 4.0)
        painter.drawPath(handle)
        can: QPainterPath = QPainterPath()
        can.addRoundedRect(QRectF(4.0, 4.0, 8.0, 10.0), 1.5, 1.5)
        painter.drawPath(can)
        for x in (6.7, 9.3):
            painter.drawLine(QPointF(x, 6.5), QPointF(x, 11.5))
        painter.end()
        return QIcon(pixmap)
