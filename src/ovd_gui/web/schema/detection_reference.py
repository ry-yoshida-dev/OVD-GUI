from pydantic import BaseModel


class DetectionReference(BaseModel):
    """
    One detection of the shown results.

    Attributes
    ----------
    path : str
        Image path.
    index : int
        Index of the detection in the result of the image.
    """

    path: str
    index: int
