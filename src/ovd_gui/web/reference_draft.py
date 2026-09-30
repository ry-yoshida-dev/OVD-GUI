from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True, eq=False)
class ReferenceDraft:
    """
    Reference image waiting for the user to box its examples.

    Attributes
    ----------
    draft_id : str
        Identifier used by the browser.
    name : str
        Display name, typically the file name; also the label of its visual query.
    image : Image.Image
        EXIF-upright RGB pixels.
    """

    draft_id: str
    name: str
    image: Image.Image
