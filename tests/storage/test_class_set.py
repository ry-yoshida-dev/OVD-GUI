import pytest
from PIL import Image

from ovd_gui.detection import ReferenceBoard, ReferenceBox, ReferenceImage
from ovd_gui.storage import ClassSet
from ovd_gui.vocabulary import ClassDefinition

PIXELS: Image.Image = Image.new("RGB", (10, 10))
REFERENCE_IMAGE: ReferenceImage = ReferenceImage.of("a.jpg", PIXELS)


def test_set_captures_the_boxes_of_its_classes_only() -> None:
    board: ReferenceBoard = ReferenceBoard()
    board.add(ReferenceBox(REFERENCE_IMAGE, "cat", 0.0, 0.0, 5.0, 5.0), PIXELS)
    board.add(ReferenceBox(REFERENCE_IMAGE, "dog", 0.0, 0.0, 5.0, 5.0), PIXELS)
    class_set: ClassSet = ClassSet.of((ClassDefinition.named("cat"),), board)
    assert [box.class_name for box in class_set.reference_boxes] == ["cat"]
    assert class_set.reference_images == (REFERENCE_IMAGE,)
    assert class_set.reference_pixels[REFERENCE_IMAGE] is PIXELS


def test_box_of_an_unknown_class_is_rejected() -> None:
    with pytest.raises(ValueError, match="belongs to no class"):
        ClassSet(
            classes=(ClassDefinition.named("cat"),),
            reference_boxes=(ReferenceBox(REFERENCE_IMAGE, "dog", 0.0, 0.0, 5.0, 5.0),),
            reference_pixels={REFERENCE_IMAGE: PIXELS},
        )


def test_box_without_pixels_is_rejected() -> None:
    with pytest.raises(ValueError, match="are missing"):
        ClassSet(
            classes=(ClassDefinition.named("cat"),),
            reference_boxes=(ReferenceBox(REFERENCE_IMAGE, "cat", 0.0, 0.0, 5.0, 5.0),),
        )


def test_repeated_class_names_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        ClassSet(classes=(ClassDefinition.named("cat"), ClassDefinition.parse("cat: kitten")))
