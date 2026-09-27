from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from PIL import Image

from ..detection import ReferenceBoard, ReferenceBox, ReferenceImage
from ..vocabulary import ClassDefinition


@dataclass(frozen=True, eq=False)
class ClassSet:
    """
    Classes with every query they are asked with: their phrases and the reference boxes of their image prompts.

    The pixels of each reference image travel with the set, so a saved set restores its image prompts without the
    files the images were imported from.

    Attributes
    ----------
    classes : tuple[ClassDefinition, ...]
        Classes in class id order.
    reference_boxes : tuple[ReferenceBox, ...]
        Reference boxes of the classes in drawing order.
    reference_pixels : Mapping[ReferenceImage, Image.Image]
        RGB pixels of every image the reference boxes lie on.

    Raises
    ------
    ValueError
        If class names repeat, a box belongs to no class, or the pixels of a boxed image are missing.
    """

    classes: tuple[ClassDefinition, ...]
    reference_boxes: tuple[ReferenceBox, ...] = ()
    reference_pixels: Mapping[ReferenceImage, Image.Image] = field(default_factory=dict[ReferenceImage, Image.Image])

    def __post_init__(self) -> None:
        class_names: list[str] = [definition.name for definition in self.classes]
        if len(set(class_names)) != len(class_names):
            raise ValueError(f"Class names must be unique: {', '.join(class_names)}")
        for box in self.reference_boxes:
            if box.class_name not in class_names:
                raise ValueError(f"Reference box of '{box.class_name}' belongs to no class of the set.")
            if box.reference_image not in self.reference_pixels:
                raise ValueError(f"Pixels of the reference image '{box.reference_image.name}' are missing.")

    @classmethod
    def of(cls, classes: Sequence[ClassDefinition], reference_board: ReferenceBoard) -> "ClassSet":
        """
        Capture classes together with their reference boxes on a board.

        Parameters
        ----------
        classes : Sequence[ClassDefinition]
            Classes in class id order.
        reference_board : ReferenceBoard
            Board holding the reference boxes; boxes of classes not in ``classes`` are left out.

        Returns
        -------
        ClassSet
            Classes, their boxes and the pixels of the boxed images.
        """
        class_names: frozenset[str] = frozenset(definition.name for definition in classes)
        boxes: tuple[ReferenceBox, ...] = tuple(box for box in reference_board.boxes if box.class_name in class_names)
        return cls(
            classes=tuple(classes),
            reference_boxes=boxes,
            reference_pixels={box.reference_image: reference_board.pixels_of(box.reference_image) for box in boxes},
        )

    @property
    def reference_images(self) -> tuple[ReferenceImage, ...]:
        """
        Images the reference boxes lie on.

        Returns
        -------
        tuple[ReferenceImage, ...]
            Images in the order their first box appears.
        """
        return tuple(dict.fromkeys(box.reference_image for box in self.reference_boxes))
