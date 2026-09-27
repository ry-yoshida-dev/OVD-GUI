from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class DisplayOptions:
    """
    How detection boxes are drawn over the image.

    Attributes
    ----------
    is_label_shown : bool
        Whether each box carries its class label.
    is_confidence_shown : bool
        Whether labels include the confidence.
    is_rejected_shown : bool
        Whether rejected detections are drawn, dashed and faded.
    is_comparison_shown : bool
        Whether the detections of the compared model are drawn, dotted, over the shown ones.
    line_width : int
        Outline width in screen pixels, in ``[MINIMUM_LINE_WIDTH, MAXIMUM_LINE_WIDTH]``.
    fill_opacity : int
        Opacity of the fill inside kept boxes, in percent; 0 draws outlines only.

    Raises
    ------
    ValueError
        If the line width or the fill opacity is out of range.
    """

    MINIMUM_LINE_WIDTH: ClassVar[int] = 1
    MAXIMUM_LINE_WIDTH: ClassVar[int] = 8

    is_label_shown: bool = True
    is_confidence_shown: bool = True
    is_rejected_shown: bool = True
    is_comparison_shown: bool = True
    line_width: int = 2
    fill_opacity: int = 0

    def __post_init__(self) -> None:
        if not self.MINIMUM_LINE_WIDTH <= self.line_width <= self.MAXIMUM_LINE_WIDTH:
            raise ValueError(
                f"line_width must be in [{self.MINIMUM_LINE_WIDTH}, {self.MAXIMUM_LINE_WIDTH}]. got {self.line_width}"
            )
        if not 0 <= self.fill_opacity <= 100:
            raise ValueError(f"fill_opacity must be in [0, 100]. got {self.fill_opacity}")
