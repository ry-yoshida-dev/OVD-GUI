from enum import Enum


class ResultColumn(Enum):
    """
    Columns of the detection table, valued by their position.
    """

    IMAGE = 0
    CLASS = 1
    QUERY = 2
    CONFIDENCE = 3
    X1 = 4
    Y1 = 5
    X2 = 6
    Y2 = 7

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
    def is_numeric(self) -> bool:
        """
        Whether the column shows numbers, aligned to the right.

        Returns
        -------
        bool
            True for the confidence and box coordinates.
        """
        match self:
            case ResultColumn.IMAGE | ResultColumn.CLASS | ResultColumn.QUERY:
                return False
            case ResultColumn.CONFIDENCE | ResultColumn.X1 | ResultColumn.Y1 | ResultColumn.X2 | ResultColumn.Y2:
                return True
