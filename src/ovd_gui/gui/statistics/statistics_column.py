from enum import Enum


class StatisticsColumn(Enum):
    """
    Columns of the per-class statistics table, valued by their position.
    """

    CLASS = 0
    IMAGES = 1
    DETECTIONS = 2
    REJECTED = 3
    BELOW_MINIMUM = 4
    KEPT = 5
    MEAN = 6
    MEDIAN = 7
    MINIMUM = 8

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
            case StatisticsColumn.CLASS:
                return "Class"
            case StatisticsColumn.IMAGES:
                return "Images"
            case StatisticsColumn.DETECTIONS:
                return "Detections"
            case StatisticsColumn.REJECTED:
                return "Rejected"
            case StatisticsColumn.BELOW_MINIMUM:
                return "Below Min."
            case StatisticsColumn.KEPT:
                return "Kept"
            case StatisticsColumn.MEAN:
                return "Mean Conf."
            case StatisticsColumn.MEDIAN:
                return "Median Conf."
            case StatisticsColumn.MINIMUM:
                return "Min. Confidence"

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
            case StatisticsColumn.CLASS:
                return "Class of the detections"
            case StatisticsColumn.IMAGES:
                return "Open images with at least one detection of the class"
            case StatisticsColumn.DETECTIONS:
                return "Every stored detection of the class"
            case StatisticsColumn.REJECTED:
                return "Detections unchecked in the detection table"
            case StatisticsColumn.BELOW_MINIMUM:
                return "Checked detections below the minimum confidence of the class"
            case StatisticsColumn.KEPT:
                return "Detections shown on the image and exported"
            case StatisticsColumn.MEAN:
                return "Mean confidence of every detection of the class"
            case StatisticsColumn.MEDIAN:
                return "Median confidence of every detection of the class"
            case StatisticsColumn.MINIMUM:
                return "Detections below this confidence are hidden and not exported; Default uses the value above"
