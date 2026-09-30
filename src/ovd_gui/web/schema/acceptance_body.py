from pydantic import BaseModel


class AcceptanceBody(BaseModel):
    """
    Detections of the shown results to keep or reject.

    Attributes
    ----------
    detections : dict[str, list[int]]
        Indices of the detections in the result of each image path.
    is_accepted : bool
        True to keep them, False to reject them.
    """

    detections: dict[str, list[int]]
    is_accepted: bool
