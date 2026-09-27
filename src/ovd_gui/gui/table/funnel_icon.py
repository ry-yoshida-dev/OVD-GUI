from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


class FunnelIcon:
    """
    Funnel icon drawn in a given color, for filter controls.
    """

    SIZE = 16
    PIXEL_RATIO = 3.0

    def __init__(self, color: QColor, is_filled: bool) -> None:
        """
        Parameters
        ----------
        color : QColor
            Stroke color, normally the button text color of the palette.
        is_filled : bool
            Whether the funnel is filled, showing that a filter is in effect.
        """
        self._color: QColor = QColor(color)
        self._is_filled: bool = is_filled

    def to_icon(self) -> QIcon:
        """
        Render the funnel.

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
        if self._is_filled:
            painter.setBrush(self._color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        funnel: QPainterPath = QPainterPath(QPointF(2.5, 3.0))
        funnel.lineTo(13.5, 3.0)
        funnel.lineTo(9.3, 8.3)
        funnel.lineTo(9.3, 13.0)
        funnel.lineTo(6.7, 11.8)
        funnel.lineTo(6.7, 8.3)
        funnel.closeSubpath()
        painter.drawPath(funnel)
        painter.end()
        return QIcon(pixmap)
