from enum import Enum


class ResultScope(Enum):
    """
    Which images the detection table lists.
    """

    CURRENT_IMAGE = "current_image"
    ALL_IMAGES = "all_images"

    @property
    def label(self) -> str:
        """
        Text shown in the scope selector.

        Returns
        -------
        str
            Human-readable scope name.
        """
        match self:
            case ResultScope.CURRENT_IMAGE:
                return "Current image"
            case ResultScope.ALL_IMAGES:
                return "All images"
