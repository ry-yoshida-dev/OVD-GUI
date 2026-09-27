from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


class OutdatedIcon:
    """
    Amber warning triangle marking results detected with other classes than the current ones.
    """

    SIZE = 16
    PIXEL_RATIO = 3.0
    FILL_COLOR = QColor(232, 160, 32)
    MARK_COLOR = QColor(255, 255, 255)

    def to_icon(self) -> QIcon:
        """
        Render the triangle.

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
        outline_pen: QPen = QPen(self.FILL_COLOR, 1.2)
        outline_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(outline_pen)
        painter.setBrush(self.FILL_COLOR)
        triangle: QPainterPath = QPainterPath(QPointF(8.0, 1.8))
        triangle.lineTo(14.6, 13.8)
        triangle.lineTo(1.4, 13.8)
        triangle.closeSubpath()
        painter.drawPath(triangle)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.MARK_COLOR)
        painter.drawRoundedRect(QRectF(7.2, 5.4, 1.6, 4.8), 0.8, 0.8)
        painter.drawEllipse(QPointF(8.0, 11.9), 0.95, 0.95)
        painter.end()
        return QIcon(pixmap)
