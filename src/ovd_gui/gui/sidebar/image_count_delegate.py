from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QRect, Qt
from PySide6.QtGui import QIcon, QPainter, QPalette
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QWidget


class ImageCountDelegate(QStyledItemDelegate):
    """
    Draws an image row as usual, with its detection count right-aligned in a muted color.

    The count is read from ``COUNT_ROLE``; the row background spans the whole width while the name is elided so that it
    never runs under the count.
    """

    COUNT_ROLE: int = Qt.ItemDataRole.UserRole.value + 1
    COUNT_MARGIN = 6

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex
    ) -> None:
        count_text: object = index.data(self.COUNT_ROLE)
        if not isinstance(count_text, str) or not count_text:
            super().paint(painter, option, index)
            return
        count_width: int = option.fontMetrics.horizontalAdvance(count_text) + 2 * self.COUNT_MARGIN
        widget: QWidget = option.widget
        style: QStyle = widget.style()
        background_option: QStyleOptionViewItem = QStyleOptionViewItem(option)
        self.initStyleOption(background_option, index)
        background_option.text = ""
        background_option.icon = QIcon()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, background_option, painter, widget)
        name_option: QStyleOptionViewItem = QStyleOptionViewItem(option)
        self.initStyleOption(name_option, index)
        name_option.rect = option.rect.adjusted(0, 0, -count_width, 0)
        super().paint(painter, name_option, index)
        is_selected: bool = bool(option.state & QStyle.StateFlag.State_Selected)
        color_role: QPalette.ColorRole = (
            QPalette.ColorRole.HighlightedText if is_selected else QPalette.ColorRole.PlaceholderText
        )
        count_rect: QRect = QRect(
            option.rect.right() - count_width, option.rect.top(), count_width - self.COUNT_MARGIN, option.rect.height()
        )
        painter.save()
        painter.setPen(option.palette.color(color_role))
        painter.drawText(count_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, count_text)
        painter.restore()
