from enum import Enum


class ProfileColumn(Enum):
    """
    Columns of the model table, valued by their position.
    """

    MODEL = 0
    OPTIONS = 1
    IMAGES = 2
    DETECTIONS = 3

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
            case ProfileColumn.MODEL:
                return "Model"
            case ProfileColumn.OPTIONS:
                return "Options"
            case ProfileColumn.IMAGES:
                return "Images"
            case ProfileColumn.DETECTIONS:
                return "Detections"

    @property
    def is_numeric(self) -> bool:
        """
        Whether the column shows counts, aligned to the right.

        Returns
        -------
        bool
            True for the image and detection counts.
        """
        match self:
            case ProfileColumn.MODEL | ProfileColumn.OPTIONS:
                return False
            case ProfileColumn.IMAGES | ProfileColumn.DETECTIONS:
                return True
