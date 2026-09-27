from enum import Enum


class ResultColumn(Enum):
    """
    Columns of the detection table, valued by their position.
    """

    ACCEPTED = 0
    IMAGE = 1
    CLASS = 2
    QUERY = 3
    CONFIDENCE = 4
    X1 = 5
    Y1 = 6
    X2 = 7
    Y2 = 8

    @property
    def header(self) -> str:
        """
        Header text of the column.

        Returns
        -------
        str
            Short column title.
        """
        match self:
            case ResultColumn.ACCEPTED:
                return "Keep"
            case ResultColumn.IMAGE:
                return "Image"
            case ResultColumn.CLASS:
                return "Class"
            case ResultColumn.QUERY:
                return "Prompt"
            case ResultColumn.CONFIDENCE:
                return "Confidence"
            case ResultColumn.X1:
                return "x1"
            case ResultColumn.Y1:
                return "y1"
            case ResultColumn.X2:
                return "x2"
            case ResultColumn.Y2:
                return "y2"

    @property
    def header_label(self) -> str:
        """
        Text drawn in the header section, next to the funnel.

        Returns
        -------
        str
            ``header``, except a check mark for the narrow ``Keep`` check box column, named by its tool tip instead.
        """
        match self:
            case ResultColumn.ACCEPTED:
                return "✓"
            case _:
                return self.header

    @property
    def is_numeric(self) -> bool:
        """
        Whether the column shows numbers, aligned to the right.

        Returns
        -------
        bool
            True for the confidence and box coordinates.
        """
        match self:
            case ResultColumn.ACCEPTED | ResultColumn.IMAGE | ResultColumn.CLASS | ResultColumn.QUERY:
                return False
            case ResultColumn.CONFIDENCE | ResultColumn.X1 | ResultColumn.Y1 | ResultColumn.X2 | ResultColumn.Y2:
                return True
