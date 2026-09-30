from pydantic import BaseModel


class ReferenceBoxesBody(BaseModel):
    """
    Boxes drawn on an opened reference image.

    Attributes
    ----------
    draft_id : str
        Identifier of the opened reference image.
    class_index : int
        Class the boxed examples show.
    boxes : list[list[float]]
        ``[x1, y1, x2, y2]`` in pixels of the upright image; empty to use the whole image.
    """

    draft_id: str
    class_index: int
    boxes: list[list[float]]
