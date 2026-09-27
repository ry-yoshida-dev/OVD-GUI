from enum import Enum

from PySide6.QtGui import QColor


class ImageState(Enum):
    """
    Where an open image stands with the results of the shown model.
    """

    NOT_ANALYZED = "not_analyzed"
    DETECTED = "detected"
    OUTDATED = "outdated"
    FAILED = "failed"

    @property
    def color(self) -> QColor:
        """
        Color of the dot marking the state in the image list.

        Returns
        -------
        QColor
            Grey, green, amber or red.
        """
        match self:
            case ImageState.NOT_ANALYZED:
                return QColor(150, 150, 150)
            case ImageState.DETECTED:
                return QColor(60, 170, 90)
            case ImageState.OUTDATED:
                return QColor(232, 160, 32)
            case ImageState.FAILED:
                return QColor(215, 60, 60)

    @property
    def is_marked_filled(self) -> bool:
        """
        Whether the dot is filled rather than outlined.

        Returns
        -------
        bool
            False only for images not analyzed yet.
        """
        match self:
            case ImageState.NOT_ANALYZED:
                return False
            case ImageState.DETECTED | ImageState.OUTDATED | ImageState.FAILED:
                return True

    @property
    def description(self) -> str:
        """
        Short explanation shown in the tool tip.

        Returns
        -------
        str
            One phrase naming the state.
        """
        match self:
            case ImageState.NOT_ANALYZED:
                return "not analyzed yet"
            case ImageState.DETECTED:
                return "detected"
            case ImageState.OUTDATED:
                return "detected with other classes"
            case ImageState.FAILED:
                return "detection failed"
