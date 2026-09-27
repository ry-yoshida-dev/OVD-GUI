from enum import Enum


class BoxGrabKind(Enum):
    """
    What dragging a grabbed reference box does.
    """

    MOVE = "move"
    RESIZE = "resize"
