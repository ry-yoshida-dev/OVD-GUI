from enum import Enum


class AnalysisState(Enum):
    """
    Why an image appears in the detection table without any detection.
    """

    NOT_ANALYZED = "not_analyzed"
    NO_DETECTIONS = "no_detections"

    @property
    def label(self) -> str:
        """
        Text shown in place of a detection.

        Returns
        -------
        str
            Human-readable state.
        """
        match self:
            case AnalysisState.NOT_ANALYZED:
                return "Not analyzed"
            case AnalysisState.NO_DETECTIONS:
                return "No detections"
