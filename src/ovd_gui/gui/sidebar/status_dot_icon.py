from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


class StatusDotIcon:
    """
    Small round dot marking the state of an image, filled or outlined.
    """

    SIZE = 12
    PIXEL_RATIO = 3.0
    RADIUS = 4.0

    def __init__(self, color: QColor, is_filled: bool) -> None:
        """
        Parameters
        ----------
        color : QColor
            Color of the dot.
        is_filled : bool
            Whether the dot is filled rather than outlined.
        """
        self._color: QColor = color
        self._is_filled: bool = is_filled

    def to_icon(self) -> QIcon:
        """
        Render the dot.

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
        painter.setPen(QPen(self._color, 1.5))
        painter.setBrush(self._color if self._is_filled else Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(self.SIZE / 2.0, self.SIZE / 2.0), self.RADIUS, self.RADIUS)
        painter.end()
        return QIcon(pixmap)
