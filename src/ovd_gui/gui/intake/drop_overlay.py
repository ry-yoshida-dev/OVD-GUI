from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPaintEvent, QPalette, QPen
from PySide6.QtWidgets import QWidget

from ...media import ImageCollection, LoadedImage


class DropOverlay(QWidget):
    """
    Layer shown over the window while files are dragged over it.

    It previews what a drop would add and turns red when the drop would add nothing.
    The layer ignores mouse events, so drag events keep reaching the window below.
    """

    MARGIN = 14
    CORNER_RADIUS = 14.0
    BORDER_WIDTH = 2.5
    BADGE_DIAMETER = 76.0
    REJECTED_COLOR = QColor("#d64545")
    TINT_ALPHA = 28

    def __init__(self, parent: QWidget) -> None:
        """
        Parameters
        ----------
        parent : QWidget
            Widget the overlay is drawn over.
        """
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._title: str = ""
        self._detail: str = ""
        self._is_acceptable: bool = True
        self.hide()

    def present(self, collection: ImageCollection, area: QRect) -> None:
        """
        Show the preview of a drop over ``area``.

        Parameters
        ----------
        collection : ImageCollection
            Images the drop would add.
        area : QRect
            Geometry to cover, in the parent's coordinates.
        """
        self._is_acceptable = not collection.is_empty
        new_count: int = len(collection.image_paths)
        if self._is_acceptable:
            self._title = f"Drop to add {new_count} image{'' if new_count == 1 else 's'}"
            self._detail = (
                f"{collection.duplicate_count} already in the list" if collection.duplicate_count else "Release to open"
            )
        elif collection.duplicate_count:
            self._title = "Already in the list"
            self._detail = "These images are open already"
        else:
            self._title = "No supported images"
            self._detail = LoadedImage.supported_format_label()
        self.setGeometry(area)
        self.raise_()
        self.show()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        accent: QColor = (
            self.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
            if self._is_acceptable
            else self.REJECTED_COLOR
        )
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Window))

        frame: QRectF = QRectF(self.rect()).adjusted(self.MARGIN, self.MARGIN, -self.MARGIN, -self.MARGIN)
        tint: QColor = QColor(accent)
        tint.setAlpha(self.TINT_ALPHA)
        border_pen: QPen = QPen(accent, self.BORDER_WIDTH, Qt.PenStyle.DashLine)
        border_pen.setDashPattern([6.0, 4.0])
        painter.setPen(border_pen)
        painter.setBrush(tint)
        painter.drawRoundedRect(frame, self.CORNER_RADIUS, self.CORNER_RADIUS)

        center: QPointF = frame.center()
        badge: QRectF = QRectF(0.0, 0.0, self.BADGE_DIAMETER, self.BADGE_DIAMETER)
        badge.moveCenter(QPointF(center.x(), center.y() - 40.0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawEllipse(badge)
        self._paint_badge_symbol(painter, badge)

        title_font: QFont = QFont(self.font())
        title_font.setPointSizeF(title_font.pointSizeF() * 1.6)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(self.palette().color(QPalette.ColorRole.WindowText))
        title_area: QRectF = QRectF(frame.left(), badge.bottom() + 18.0, frame.width(), 36.0)
        painter.drawText(title_area, Qt.AlignmentFlag.AlignCenter, self._title)

        painter.setFont(self.font())
        painter.setPen(self.palette().color(QPalette.ColorRole.PlaceholderText))
        detail_area: QRectF = QRectF(frame.left(), title_area.bottom() + 2.0, frame.width(), 24.0)
        painter.drawText(detail_area, Qt.AlignmentFlag.AlignCenter, self._detail)

    def _paint_badge_symbol(self, painter: QPainter, badge: QRectF) -> None:
        symbol_pen: QPen = QPen(QColor("white"), 4.0)
        symbol_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        symbol_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(symbol_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        center: QPointF = badge.center()
        arm: float = badge.width() * 0.18
        if self._is_acceptable:
            symbol: QPainterPath = QPainterPath(QPointF(center.x(), center.y() - arm * 1.3))
            symbol.lineTo(center.x(), center.y() + arm * 1.1)
            symbol.moveTo(center.x() - arm, center.y() + arm * 0.1)
            symbol.lineTo(center.x(), center.y() + arm * 1.1)
            symbol.lineTo(center.x() + arm, center.y() + arm * 0.1)
            painter.drawPath(symbol)
            return
        painter.drawLine(QPointF(center.x() - arm, center.y() - arm), QPointF(center.x() + arm, center.y() + arm))
        painter.drawLine(QPointF(center.x() + arm, center.y() - arm), QPointF(center.x() - arm, center.y() + arm))
