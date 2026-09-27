from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPaintEvent, QPalette, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...media import LoadedImage


class DropZone(QWidget):
    """
    Placeholder inviting the user to drop images or folders, with buttons for the file dialogs.

    Shown instead of the image while no image is open, and in the reference image picker.
    Drops themselves are handled by the enclosing window.

    Signals
    -------
    open_images_requested : Signal()
        The user asked to choose image files.
    open_folder_requested : Signal()
        The user asked to choose a folder.
    """

    open_images_requested: Signal = Signal()
    open_folder_requested: Signal = Signal()

    DEFAULT_TITLE = "Drop images or folders here"
    MARGIN = 24
    CORNER_RADIUS = 16.0
    GLYPH_SIZE = 96

    def __init__(self, title: str = DEFAULT_TITLE, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        title : str, optional
            Invitation shown above the supported formats.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._glyph_slot: QWidget = QWidget()
        self._glyph_slot.setFixedSize(self.GLYPH_SIZE, self.GLYPH_SIZE)

        title_label: QLabel = QLabel(title)
        title_font: QFont = QFont(title_label.font())
        title_font.setPointSizeF(title_font.pointSizeF() * 1.6)
        title_font.setWeight(QFont.Weight.DemiBold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        formats_label: QLabel = QLabel(LoadedImage.supported_format_label())
        formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formats_label.setForegroundRole(QPalette.ColorRole.PlaceholderText)

        open_images_button: QPushButton = QPushButton("Open Images…")
        open_images_button.setDefault(True)
        open_images_button.clicked.connect(self.open_images_requested)
        open_folder_button: QPushButton = QPushButton("Open Folder…")
        open_folder_button.clicked.connect(self.open_folder_requested)
        button_row: QHBoxLayout = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(open_images_button)
        button_row.addWidget(open_folder_button)
        button_row.addStretch(1)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)
        layout.addStretch(1)
        layout.addWidget(self._glyph_slot, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(16)
        layout.addWidget(title_label)
        layout.addWidget(formats_label)
        layout.addSpacing(20)
        layout.addLayout(button_row)
        layout.addStretch(1)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        outline: QColor = self.palette().color(QPalette.ColorRole.Mid)
        frame: QRectF = QRectF(self.rect()).adjusted(self.MARGIN, self.MARGIN, -self.MARGIN, -self.MARGIN)
        frame_pen: QPen = QPen(outline, 2.0, Qt.PenStyle.DashLine)
        frame_pen.setDashPattern([6.0, 4.0])
        painter.setPen(frame_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(frame, self.CORNER_RADIUS, self.CORNER_RADIUS)
        self._paint_glyph(painter, QRectF(self._glyph_slot.geometry()))

    def _paint_glyph(self, painter: QPainter, area: QRectF) -> None:
        accent: QColor = self.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
        backdrop: QColor = QColor(accent)
        backdrop.setAlpha(36)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(backdrop)
        painter.drawEllipse(area)

        icon_size: float = area.width() * 0.44
        icon: QRectF = QRectF(0.0, 0.0, icon_size, icon_size)
        icon.moveCenter(area.center())
        stroke_pen: QPen = QPen(accent, icon_size * 0.1)
        stroke_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroke_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(stroke_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        tray_top: float = icon.top() + icon_size * 0.62
        tray: QPainterPath = QPainterPath(QPointF(icon.left(), tray_top))
        tray.lineTo(icon.left(), icon.bottom())
        tray.lineTo(icon.right(), icon.bottom())
        tray.lineTo(icon.right(), tray_top)
        painter.drawPath(tray)

        arrow_x: float = icon.center().x()
        arrow_head: float = icon_size * 0.26
        arrow: QPainterPath = QPainterPath(QPointF(arrow_x, icon.top() + icon_size * 0.72))
        arrow.lineTo(arrow_x, icon.top())
        arrow.moveTo(arrow_x - arrow_head, icon.top() + arrow_head)
        arrow.lineTo(arrow_x, icon.top())
        arrow.lineTo(arrow_x + arrow_head, icon.top() + arrow_head)
        painter.drawPath(arrow)
