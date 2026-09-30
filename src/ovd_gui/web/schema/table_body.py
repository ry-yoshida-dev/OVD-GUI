from pydantic import BaseModel

from .detection_reference import DetectionReference


class TableBody(BaseModel):
    """
    Detections listed in the detection table, in display order.

    Attributes
    ----------
    detections : list[DetectionReference]
        Listed detections.
    """

    detections: list[DetectionReference]
