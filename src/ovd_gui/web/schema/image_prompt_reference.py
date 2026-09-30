from pydantic import BaseModel


class ImagePromptReference(BaseModel):
    """
    One reference image of a class, i.e. one visual query.

    Attributes
    ----------
    class_index : int
        Class id.
    name : str
        Display name of the reference image.
    digest : str
        SHA-256 of the reference image pixels.
    """

    class_index: int
    name: str
    digest: str
