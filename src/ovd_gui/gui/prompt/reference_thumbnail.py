from collections.abc import Sequence

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap


class ReferenceThumbnail:
    """
    Square thumbnail of a reference image with its boxes outlined in the class color.

    The image is fitted inside a rounded tile without cropping, so every box stays visible.
    """

    PIXEL_RATIO = 2.0
    CORNER_RADIUS = 6.0
    BOX_PEN_WIDTH = 1.6

    def __init__(self, edge: int, background: QColor) -> None:
        """
        Parameters
        ----------
        edge : int
            Width and height of the tile in logical pixels.
        background : QColor
            Tile color around the fitted image.

        Raises
        ------
        ValueError
            If ``edge`` is not positive.
        """
        if edge <= 0:
            raise ValueError(f"edge must be positive. got {edge}")
        self._edge: int = edge
        self._background: QColor = QColor(background)

    def render(self, image: Image.Image, boxes: Sequence[tuple[float, float, float, float]], color: QColor) -> QIcon:
        """
        Draw the thumbnail of one visual query.

        Parameters
        ----------
        image : Image.Image
            Reference image pixels.
        boxes : Sequence[tuple[float, float, float, float]]
            XYXY boxes in image pixels.
        color : QColor
            Class color of the box outlines.

        Returns
        -------
        QIcon
            Tile of ``edge`` logical pixels.
        """
        physical_edge: int = round(self._edge * self.PIXEL_RATIO)
        pixmap: QPixmap = QPixmap(physical_edge, physical_edge)
        pixmap.setDevicePixelRatio(self.PIXEL_RATIO)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter: QPainter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        tile: QPainterPath = QPainterPath()
        tile.addRoundedRect(QRectF(0.0, 0.0, self._edge, self._edge), self.CORNER_RADIUS, self.CORNER_RADIUS)
        painter.setClipPath(tile)
        painter.fillPath(tile, self._background)

        width, height = image.size
        scale: float = min(self._edge / width, self._edge / height)
        offset_x: float = (self._edge - width * scale) / 2.0
        offset_y: float = (self._edge - height * scale) / 2.0
        reduced_image: Image.Image = image.copy()
        reduced_image.thumbnail((physical_edge, physical_edge))
        painter.drawImage(QRectF(offset_x, offset_y, width * scale, height * scale), self._to_qimage(reduced_image))

        pen: QPen = QPen(color, self.BOX_PEN_WIDTH)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for left, top, right, bottom in boxes:
            painter.drawRect(
                QRectF(offset_x + left * scale, offset_y + top * scale, (right - left) * scale, (bottom - top) * scale)
            )
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _to_qimage(image: Image.Image) -> QImage:
        width, height = image.size
        pixel_bytes: bytes = image.convert("RGB").tobytes("raw", "RGB")
        return QImage(pixel_bytes, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
