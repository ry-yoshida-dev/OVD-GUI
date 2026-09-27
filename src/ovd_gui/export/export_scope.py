from enum import Enum


class ExportScope(Enum):
    """
    Which detections of the shown model are exported.
    """

    KEPT = "kept"
    LISTED = "listed"

    @property
    def label(self) -> str:
        """
        Text of the choice in the export dialog.

        Returns
        -------
        str
            Short description of the detections exported.
        """
        match self:
            case ExportScope.KEPT:
                return "Every kept detection"
            case ExportScope.LISTED:
                return "Only detections listed in the table"

    @property
    def description(self) -> str:
        """
        Tool tip explaining the choice.

        Returns
        -------
        str
            What is left out.
        """
        match self:
            case ExportScope.KEPT:
                return "Leave out rejected detections and those below the minimum confidence of their class"
            case ExportScope.LISTED:
                return "Also leave out the detections hidden by the column filters of the detection table"
