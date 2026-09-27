from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF

from .box_grab_kind import BoxGrabKind


@dataclass(frozen=True)
class BoxGrab:
    """
    Reference box taken by the mouse for moving or resizing.

    Attributes
    ----------
    item_position : int
        Position of the grabbed box among the drawn reference boxes.
    kind : BoxGrabKind
        Whether the drag moves the box or resizes it.
    anchor : QPointF
        Fixed opposite corner while resizing, or the pressed point while moving, in scene coordinates.
    original_rectangle : QRectF
        Rectangle of the box when it was grabbed.
    """

    item_position: int
    kind: BoxGrabKind
    anchor: QPointF
    original_rectangle: QRectF
