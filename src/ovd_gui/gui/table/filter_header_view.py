from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHeaderView, QStyle, QWidget


class FilterHeaderView(QHeaderView):
    """
    Horizontal header whose sections open a column filter from the funnel icon at their left edge.

    Clicking the funnel, or right-clicking anywhere on a section, asks for the filter of that column; clicking the
    rest of a section sorts as usual. The funnel is the decoration of the header, supplied by the model.

    Signals
    -------
    filter_requested : Signal(int, QPoint)
        The filter of a column was asked for, with the logical index of the column and the global position under
        the left edge of its section.
    """

    filter_requested: Signal = Signal(int, QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setSectionsClickable(True)
        self._is_press_consumed: bool = False

    def request_filter(self, logical_index: int) -> None:
        """
        Ask for the filter of one column, as clicking its funnel does.

        Parameters
        ----------
        logical_index : int
            Column to filter.

        Raises
        ------
        IndexError
            If the column does not exist.
        """
        if not 0 <= logical_index < self.count():
            raise IndexError(f"logical_index must be in [0, {self.count()}). got {logical_index}")
        left: int = self.sectionViewportPosition(logical_index)
        self.filter_requested.emit(logical_index, self.viewport().mapToGlobal(QPoint(left, self.height())))

    def mousePressEvent(self, e: QMouseEvent) -> None:
        position: QPoint = e.position().toPoint()
        logical_index: int = self.logicalIndexAt(position)
        is_filter_click: bool = logical_index >= 0 and (
            e.button() == Qt.MouseButton.RightButton
            or (e.button() == Qt.MouseButton.LeftButton and self._is_on_funnel(logical_index, position))
        )
        if not is_filter_click:
            super().mousePressEvent(e)
            return
        self._is_press_consumed = True
        e.accept()
        self.request_filter(logical_index)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if self._is_press_consumed:
            self._is_press_consumed = False
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def _is_on_funnel(self, logical_index: int, position: QPoint) -> bool:
        margin: int = self.style().pixelMetric(QStyle.PixelMetric.PM_HeaderMargin, None, self)
        grip_margin: int = self.style().pixelMetric(QStyle.PixelMetric.PM_HeaderGripMargin, None, self)
        icon_size: int = self.style().pixelMetric(QStyle.PixelMetric.PM_SmallIconSize, None, self)
        offset: int = position.x() - self.sectionViewportPosition(logical_index)
        return grip_margin <= offset <= 2 * margin + icon_size
