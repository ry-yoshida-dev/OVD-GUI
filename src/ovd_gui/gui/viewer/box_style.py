from enum import Enum

from PySide6.QtCore import Qt


class BoxStyle(Enum):
    """
    Role of a detection box on the canvas, deciding how it is drawn.
    """

    KEPT = "kept"
    REJECTED = "rejected"
    COMPARED = "compared"

    @property
    def pen_style(self) -> Qt.PenStyle:
        """
        Outline pattern of the box.

        Returns
        -------
        Qt.PenStyle
            Solid for kept boxes, dashed for rejected ones and dotted for the compared model.
        """
        match self:
            case BoxStyle.KEPT:
                return Qt.PenStyle.SolidLine
            case BoxStyle.REJECTED:
                return Qt.PenStyle.DashLine
            case BoxStyle.COMPARED:
                return Qt.PenStyle.DotLine

    @property
    def opacity(self) -> float:
        """
        Opacity of the whole box with its label.

        Returns
        -------
        float
            1 for kept boxes, lower for rejected and compared ones.
        """
        match self:
            case BoxStyle.KEPT:
                return 1.0
            case BoxStyle.REJECTED:
                return 0.45
            case BoxStyle.COMPARED:
                return 0.85
