from dataclasses import dataclass


@dataclass(frozen=True)
class ImageInfo:
    """
    Version and upright size of an image file, read without decoding its pixels.

    Attributes
    ----------
    version : str
        Modification time and size of the file, changing whenever the file does.
    width : int
        Width of the EXIF-upright image in pixels.
    height : int
        Height of the EXIF-upright image in pixels.
    """

    version: str
    width: int
    height: int
