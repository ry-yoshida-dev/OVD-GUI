from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QWidget


class ClassSetRowDelegate(QStyledItemDelegate):
    """
    Two-line row of a saved class set: the name with its save time, and a muted line describing its content.

    The row is drawn on a rounded highlight when selected and a faint one when hovered; a set that cannot be read
    shows its detail line in a warning color. Renaming edits the name line in place.
    """

    DETAIL_ROLE = Qt.ItemDataRole.UserRole + 1
    SAVED_AT_ROLE = Qt.ItemDataRole.UserRole + 2
    IS_READABLE_ROLE = Qt.ItemDataRole.UserRole + 3

    HORIZONTAL_PADDING = 10
    VERTICAL_PADDING = 7
    LINE_SPACING = 2
    ROW_MARGIN = 2
    CORNER_RADIUS = 6.0
    DETAIL_FONT_SCALE = 0.9
    HOVER_ALPHA = 28
    WARNING_COLOR = QColor("#d9822b")

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex) -> QSize:
        name_height: int = QFontMetrics(self._name_font(option.font)).height()
        detail_height: int = QFontMetrics(self._detail_font(option.font)).height()
        return QSize(
            200,
            name_height + self.LINE_SPACING + detail_height + 2 * (self.VERTICAL_PADDING + self.ROW_MARGIN),
        )

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex
    ) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        palette: QPalette = option.palette
        is_selected: bool = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hovered: bool = bool(option.state & QStyle.StateFlag.State_MouseOver)
        row_rectangle: QRectF = QRectF(option.rect).adjusted(
            self.ROW_MARGIN, self.ROW_MARGIN, -self.ROW_MARGIN, -self.ROW_MARGIN
        )
        background: QPainterPath = QPainterPath()
        background.addRoundedRect(row_rectangle, self.CORNER_RADIUS, self.CORNER_RADIUS)
        if is_selected:
            painter.fillPath(background, palette.color(QPalette.ColorRole.Highlight))
        elif is_hovered:
            hover_color: QColor = QColor(palette.color(QPalette.ColorRole.Text))
            hover_color.setAlpha(self.HOVER_ALPHA)
            painter.fillPath(background, hover_color)

        text_color: QColor = palette.color(
            QPalette.ColorRole.HighlightedText if is_selected else QPalette.ColorRole.Text
        )
        muted_color: QColor = QColor(text_color if is_selected else palette.color(QPalette.ColorRole.PlaceholderText))
        if is_selected:
            muted_color.setAlphaF(0.8)
        is_readable: bool = bool(index.data(self.IS_READABLE_ROLE))
        detail_color: QColor = muted_color if is_readable or is_selected else self.WARNING_COLOR

        content: QRect = row_rectangle.toRect().adjusted(
            self.HORIZONTAL_PADDING, self.VERTICAL_PADDING, -self.HORIZONTAL_PADDING, -self.VERTICAL_PADDING
        )
        name_font: QFont = self._name_font(option.font)
        detail_font: QFont = self._detail_font(option.font)
        name_height: int = QFontMetrics(name_font).height()
        saved_at: str = str(index.data(self.SAVED_AT_ROLE) or "")
        painter.setFont(detail_font)
        saved_at_width: int = QFontMetrics(detail_font).horizontalAdvance(saved_at)
        painter.setPen(muted_color)
        painter.drawText(
            QRect(content.left(), content.top(), content.width(), name_height),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            saved_at,
        )

        name_rectangle: QRect = QRect(
            content.left(),
            content.top(),
            max(0, content.width() - saved_at_width - self.HORIZONTAL_PADDING),
            name_height,
        )
        painter.setFont(name_font)
        painter.setPen(text_color)
        name: str = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        painter.drawText(
            name_rectangle,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            QFontMetrics(name_font).elidedText(name, Qt.TextElideMode.ElideRight, name_rectangle.width()),
        )

        detail_rectangle: QRect = QRect(
            content.left(),
            content.top() + name_height + self.LINE_SPACING,
            content.width(),
            QFontMetrics(detail_font).height(),
        )
        painter.setFont(detail_font)
        painter.setPen(detail_color)
        detail: str = str(index.data(self.DETAIL_ROLE) or "")
        painter.drawText(
            detail_rectangle,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            QFontMetrics(detail_font).elidedText(detail, Qt.TextElideMode.ElideRight, detail_rectangle.width()),
        )
        painter.restore()

    def updateEditorGeometry(
        self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex
    ) -> None:
        name_height: int = QFontMetrics(self._name_font(option.font)).height()
        editor.setGeometry(
            option.rect.left() + self.ROW_MARGIN + self.HORIZONTAL_PADDING - 3,
            option.rect.top() + self.ROW_MARGIN + self.VERTICAL_PADDING - 3,
            option.rect.width() - 2 * (self.ROW_MARGIN + self.HORIZONTAL_PADDING) + 6,
            name_height + 6,
        )

    @staticmethod
    def _name_font(base_font: QFont) -> QFont:
        name_font: QFont = QFont(base_font)
        name_font.setWeight(QFont.Weight.DemiBold)
        return name_font

    @classmethod
    def _detail_font(cls, base_font: QFont) -> QFont:
        detail_font: QFont = QFont(base_font)
        detail_font.setPointSizeF(base_font.pointSizeF() * cls.DETAIL_FONT_SCALE)
        return detail_font
