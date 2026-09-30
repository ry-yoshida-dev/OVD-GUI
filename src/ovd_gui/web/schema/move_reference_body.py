from pydantic import BaseModel


class MoveReferenceBody(BaseModel):
    """
    Reference image dragged to another class.

    Attributes
    ----------
    class_index : int
        Class id the reference image belongs to.
    name : str
        Display name of the reference image.
    digest : str
        SHA-256 of the reference image pixels.
    target_class_index : int
        Class receiving the reference image.
    """

    class_index: int
    name: str
    digest: str
    target_class_index: int
