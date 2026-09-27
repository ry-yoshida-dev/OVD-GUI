from enum import Enum


class ComparisonColumn(Enum):
    """
    Columns of the model comparison table, valued by their position.
    """

    CLASS = 0
    SHOWN = 1
    COMPARED = 2
    MATCHED = 3
    SHOWN_ONLY = 4
    COMPARED_ONLY = 5

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
            case ComparisonColumn.CLASS:
                return "Class"
            case ComparisonColumn.SHOWN:
                return "Shown"
            case ComparisonColumn.COMPARED:
                return "Compared"
            case ComparisonColumn.MATCHED:
                return "Matched"
            case ComparisonColumn.SHOWN_ONLY:
                return "Only Shown"
            case ComparisonColumn.COMPARED_ONLY:
                return "Only Compared"

    @property
    def tool_tip(self) -> str:
        """
        Explanation of the column shown on its header.

        Returns
        -------
        str
            One sentence.
        """
        match self:
            case ComparisonColumn.CLASS:
                return "Class of the detections"
            case ComparisonColumn.SHOWN:
                return "Detections of the shown model"
            case ComparisonColumn.COMPARED:
                return "Detections of the compared model"
            case ComparisonColumn.MATCHED:
                return "Detections of both models overlapping one to one"
            case ComparisonColumn.SHOWN_ONLY:
                return "Detections only the shown model found"
            case ComparisonColumn.COMPARED_ONLY:
                return "Detections only the compared model found"
