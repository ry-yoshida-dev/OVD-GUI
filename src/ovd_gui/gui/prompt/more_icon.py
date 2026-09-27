from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap


class MoreIcon:
    """
    Horizontal three-dot icon drawn in a given color, for overflow menus.
    """

    SIZE = 16
    PIXEL_RATIO = 3.0
    DOT_RADIUS = 1.4
    DOT_CENTERS_X = (3.5, 8.0, 12.5)

    def __init__(self, color: QColor) -> None:
        """
        Parameters
        ----------
        color : QColor
            Fill color, normally the button text color of the palette.
        """
        self._color: QColor = QColor(color)

    def to_icon(self) -> QIcon:
        """
        Render the three dots.

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
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        center_y: float = self.SIZE / 2
        for center_x in self.DOT_CENTERS_X:
            painter.drawEllipse(QPointF(center_x, center_y), self.DOT_RADIUS, self.DOT_RADIUS)
        painter.end()
        return QIcon(pixmap)
