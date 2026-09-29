from enum import Enum

from ...detection import ProfileSummary


class ProfileColumn(Enum):
    """
    Columns of the model table, valued by their position.
    """

    BACKEND = 0
    MODEL = 1
    DEVICE = 2
    PRECISION = 3
    CONFIDENCE = 4
    NMS = 5
    IMAGES = 6
    OUTDATED = 7
    DETECTIONS = 8

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
            case ProfileColumn.BACKEND:
                return "Backend"
            case ProfileColumn.MODEL:
                return "Model"
            case ProfileColumn.DEVICE:
                return "Device"
            case ProfileColumn.PRECISION:
                return "Precision"
            case ProfileColumn.CONFIDENCE:
                return "Conf."
            case ProfileColumn.NMS:
                return "NMS IoU"
            case ProfileColumn.IMAGES:
                return "Images"
            case ProfileColumn.OUTDATED:
                return "Outdated"
            case ProfileColumn.DETECTIONS:
                return "Detections"

    @property
    def header_tool_tip(self) -> str:
        """
        Explanation shown when hovering the header.

        Returns
        -------
        str
            What the column shows.
        """
        match self:
            case ProfileColumn.BACKEND:
                return "Detector family"
            case ProfileColumn.MODEL:
                return "Checkpoint of the model"
            case ProfileColumn.DEVICE:
                return "Device the model ran on"
            case ProfileColumn.PRECISION:
                return "Floating-point precision of the model"
            case ProfileColumn.CONFIDENCE:
                return "Confidence threshold of the detector"
            case ProfileColumn.NMS:
                return "IoU threshold of non-maximum suppression"
            case ProfileColumn.IMAGES:
                return "Images detected with the model"
            case ProfileColumn.OUTDATED:
                return "Images detected with other classes than the current ones"
            case ProfileColumn.DETECTIONS:
                return "Detections in those images"

    @property
    def is_right_aligned(self) -> bool:
        """
        Whether the column shows numbers, aligned to the right.

        Returns
        -------
        bool
            True for the thresholds and the counts.
        """
        match self:
            case ProfileColumn.BACKEND | ProfileColumn.MODEL | ProfileColumn.DEVICE | ProfileColumn.PRECISION:
                return False
            case (
                ProfileColumn.CONFIDENCE
                | ProfileColumn.NMS
                | ProfileColumn.IMAGES
                | ProfileColumn.OUTDATED
                | ProfileColumn.DETECTIONS
            ):
                return True

    def text_of(self, summary: ProfileSummary) -> str:
        """
        Cell text of a profile in this column.

        Parameters
        ----------
        summary : ProfileSummary
            Profile and counts of the row.

        Returns
        -------
        str
            Cell text; empty in ``OUTDATED`` when no image is outdated.
        """
        match self:
            case ProfileColumn.BACKEND:
                return summary.profile.backend.value
            case ProfileColumn.MODEL:
                return summary.profile.model_name
            case ProfileColumn.DEVICE:
                return summary.profile.device.value
            case ProfileColumn.PRECISION:
                return summary.profile.precision_text
            case ProfileColumn.CONFIDENCE:
                return summary.profile.confidence_text
            case ProfileColumn.NMS:
                return summary.profile.nms_text
            case ProfileColumn.IMAGES:
                return str(summary.image_count)
            case ProfileColumn.OUTDATED:
                return str(summary.outdated_image_count) if summary.outdated_image_count else ""
            case ProfileColumn.DETECTIONS:
                return str(summary.detection_count)
