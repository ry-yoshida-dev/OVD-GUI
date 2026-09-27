from dataclasses import dataclass, replace

from .reference_image import ReferenceImage


@dataclass(frozen=True)
class ReferenceBox:
    """
    Box drawn by the user around an example of a class, used as an image prompt.

    Attributes
    ----------
    reference_image : ReferenceImage
        Image the box was drawn on.
    class_name : str
        Class the boxed instance shows.
    left : float
        Left edge in image pixels.
    top : float
        Top edge in image pixels.
    right : float
        Right edge in image pixels.
    bottom : float
        Bottom edge in image pixels.

    Raises
    ------
    ValueError
        If the class name is blank or the box has no area.
    """

    reference_image: ReferenceImage
    class_name: str
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if not self.class_name.strip():
            raise ValueError("class_name must not be blank.")
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError(f"box must have a positive area. got {self.xyxy}")

    @property
    def xyxy(self) -> tuple[float, float, float, float]:
        """
        Corners of the box.

        Returns
        -------
        tuple[float, float, float, float]
            ``(left, top, right, bottom)`` in image pixels.
        """
        return (self.left, self.top, self.right, self.bottom)

    def renamed(self, class_name: str) -> "ReferenceBox":
        """
        Same box assigned to another class name.

        Parameters
        ----------
        class_name : str
            New class name.

        Returns
        -------
        ReferenceBox
            Copy with ``class_name`` replaced.
        """
        return replace(self, class_name=class_name)
