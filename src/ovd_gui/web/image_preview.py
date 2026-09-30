from dataclasses import dataclass


@dataclass(frozen=True)
class ImagePreview:
    """
    Encoded image a browser can display.

    Attributes
    ----------
    content : bytes
        Encoded pixels.
    media_type : str
        MIME type of ``content``.
    """

    content: bytes
    media_type: str
