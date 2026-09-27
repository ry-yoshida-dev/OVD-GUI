from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPalette, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ...analysis import ConfidenceHistogram


class ConfidenceHistogramView(QWidget):
    """
    Bar chart of a confidence histogram over ``[0, 1]`` with a vertical line at a minimum confidence.

    Bars below the minimum are drawn faded, since those detections are hidden; the count axis is labeled with the
    fullest bin and the confidence axis at 0, 0.5 and 1.
    """

    MARGIN = 8.0
    AXIS_LABEL_HEIGHT = 16.0
    FADED_ALPHA = 70
    MINIMUM_LINE_COLOR = QColor(215, 60, 60)
    PREFERRED_SIZE = QSize(360, 140)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._histogram: ConfidenceHistogram = ConfidenceHistogram.of(())
        self._minimum_confidence: float = 0.0
        self._bar_color: QColor = self.palette().color(QPalette.ColorRole.Highlight)
        self._title: str = ""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(100)

    @property
    def histogram(self) -> ConfidenceHistogram:
        """
        Drawn histogram.

        Returns
        -------
        ConfidenceHistogram
            Counts per bin.
        """
        return self._histogram

    @property
    def minimum_confidence(self) -> float:
        """
        Confidence marked by the vertical line.

        Returns
        -------
        float
            Minimum in ``[0, 1]``.
        """
        return self._minimum_confidence

    def sizeHint(self) -> QSize:
        return self.PREFERRED_SIZE

    def show_histogram(
        self, histogram: ConfidenceHistogram, minimum_confidence: float, bar_color: QColor, title: str
    ) -> None:
        """
        Draw another histogram.

        Parameters
        ----------
        histogram : ConfidenceHistogram
            Counts per bin.
        minimum_confidence : float
            Confidence below which bars are faded, in ``[0, 1]``.
        bar_color : QColor
            Color of the bars, typically the class color.
        title : str
            Caption drawn in the top-left corner.
        """
        self._histogram = histogram
        self._minimum_confidence = minimum_confidence
        self._bar_color = bar_color
        self._title = title
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        text_color: QColor = self.palette().color(QPalette.ColorRole.WindowText)
        muted_color: QColor = self.palette().color(QPalette.ColorRole.PlaceholderText)
        plot: QRectF = QRectF(self.rect()).adjusted(
            self.MARGIN, self.MARGIN + self.AXIS_LABEL_HEIGHT, -self.MARGIN, -self.MARGIN - self.AXIS_LABEL_HEIGHT
        )
        painter.setPen(text_color)
        painter.drawText(
            QRectF(self.MARGIN, self.MARGIN, plot.width(), self.AXIS_LABEL_HEIGHT),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._title,
        )
        painter.setPen(muted_color)
        painter.drawText(
            QRectF(self.MARGIN, self.MARGIN, plot.width(), self.AXIS_LABEL_HEIGHT),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"max {self._histogram.largest_count} per bin",
        )
        axis_label_rect: QRectF = QRectF(plot.left(), plot.bottom() + 2.0, plot.width(), self.AXIS_LABEL_HEIGHT)
        for tick_text, alignment in (
            ("0", Qt.AlignmentFlag.AlignLeft),
            ("0.5", Qt.AlignmentFlag.AlignHCenter),
            ("1", Qt.AlignmentFlag.AlignRight),
        ):
            painter.drawText(axis_label_rect, alignment | Qt.AlignmentFlag.AlignTop, tick_text)
        painter.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right(), plot.bottom()))
        largest_count: int = self._histogram.largest_count
        if largest_count:
            bin_width: float = plot.width() / len(self._histogram.bin_counts)
            painter.setPen(Qt.PenStyle.NoPen)
            for bin_index, count in enumerate(self._histogram.bin_counts):
                if not count:
                    continue
                bar_height: float = plot.height() * count / largest_count
                bar_color: QColor = QColor(self._bar_color)
                if (bin_index + 1) * self._histogram.bin_width <= self._minimum_confidence:
                    bar_color.setAlpha(self.FADED_ALPHA)
                painter.setBrush(bar_color)
                painter.drawRect(
                    QRectF(
                        plot.left() + bin_index * bin_width + 1.0,
                        plot.bottom() - bar_height,
                        bin_width - 2.0,
                        bar_height,
                    )
                )
        if self._minimum_confidence > 0.0:
            minimum_x: float = plot.left() + self._minimum_confidence * plot.width()
            line_pen: QPen = QPen(self.MINIMUM_LINE_COLOR, 1.5)
            line_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(line_pen)
            painter.drawLine(QPointF(minimum_x, plot.top()), QPointF(minimum_x, plot.bottom()))
        painter.end()
