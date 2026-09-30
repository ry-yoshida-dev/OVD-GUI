from enum import Enum


class ImageState(Enum):
    """
    Where an open image stands with the results of the shown model.
    """

    NOT_ANALYZED = "not_analyzed"
    DETECTED = "detected"
    OUTDATED = "outdated"
    FAILED = "failed"

    @property
    def color(self) -> str:
        """
        Color of the dot marking the state in the image list.

        Returns
        -------
        str
            Grey, green, amber or red as ``#rrggbb``.
        """
        match self:
            case ImageState.NOT_ANALYZED:
                return "#969696"
            case ImageState.DETECTED:
                return "#3caa5a"
            case ImageState.OUTDATED:
                return "#e8a020"
            case ImageState.FAILED:
                return "#d73c3c"

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
