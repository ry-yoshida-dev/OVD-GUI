from pathlib import Path

import numpy as np
import pytest
from open_vocabulary_detector import PromptKind, TextQuery, VisualQuery
from PIL import Image

from ovd_gui.detection import LabeledPrompt, ReferenceBoard, ReferenceBox
from ovd_gui.vocabulary import ClassDefinition

ALL_KINDS: frozenset[PromptKind] = frozenset({PromptKind.TEXT, PromptKind.VISUAL})
TEXT_ONLY: frozenset[PromptKind] = frozenset({PromptKind.TEXT})


def _box(class_name: str, image_path: Path = Path("a.jpg"), left: float = 10.0) -> ReferenceBox:
    return ReferenceBox(image_path=image_path, class_name=class_name, left=left, top=10.0, right=50.0, bottom=40.0)


def _image() -> Image.Image:
    return Image.new("RGB", (100, 80))


def _classes(*texts: str) -> tuple[ClassDefinition, ...]:
    return tuple(ClassDefinition.parse(text) for text in texts)


def test_box_without_area_is_rejected() -> None:
    with pytest.raises(ValueError):
        ReferenceBox(image_path=Path("a.jpg"), class_name="cat", left=10.0, top=10.0, right=10.0, bottom=40.0)


def test_box_outside_image_is_rejected() -> None:
    board: ReferenceBoard = ReferenceBoard()
    with pytest.raises(ValueError):
        board.add(
            ReferenceBox(image_path=Path("a.jpg"), class_name="cat", left=0, top=0, right=101, bottom=10), _image()
        )


def test_phrases_become_text_queries_labelled_by_phrase() -> None:
    labeled_prompt: LabeledPrompt = ReferenceBoard().build_prompt(_classes("car: car, suv", "dog"), ALL_KINDS)
    assert labeled_prompt.prompt.class_names == ("car", "dog")
    assert labeled_prompt.prompt.queries == (TextQuery("car"), TextQuery("suv"), TextQuery("dog"))
    assert labeled_prompt.query_labels == ("car", "suv", "dog")


def test_each_reference_image_is_one_visual_query_after_the_phrases() -> None:
    board: ReferenceBoard = ReferenceBoard()
    board.add(_box("car"), _image())
    board.add(_box("car", left=20.0), _image())
    board.add(_box("car", image_path=Path("b.jpg")), _image())
    labeled_prompt: LabeledPrompt = board.build_prompt(_classes("car: suv", "dog"), ALL_KINDS)
    queries = labeled_prompt.prompt.queries
    assert labeled_prompt.query_labels == ("suv", "a.jpg", "b.jpg", "dog")
    assert labeled_prompt.prompt.query_class_ids == (0, 0, 0, 1)
    first_image_query = queries[1]
    assert isinstance(first_image_query, VisualQuery)
    np.testing.assert_allclose(first_image_query.references[0].xyxy, [[10, 10, 50, 40], [20, 10, 50, 40]])


def test_reference_images_are_left_out_without_visual_support() -> None:
    board: ReferenceBoard = ReferenceBoard()
    board.add(_box("car"), _image())
    labeled_prompt: LabeledPrompt = board.build_prompt(_classes("car: suv"), TEXT_ONLY)
    assert labeled_prompt.query_labels == ("suv",)


def test_class_without_usable_query_is_rejected() -> None:
    board: ReferenceBoard = ReferenceBoard()
    board.add(_box("mug"), _image())
    assert board.build_prompt(_classes("mug:"), ALL_KINDS).query_labels == ("a.jpg",)
    with pytest.raises(ValueError, match="only by reference images"):
        board.build_prompt(_classes("mug:"), TEXT_ONLY)
    with pytest.raises(ValueError, match="no phrase and no reference image"):
        board.build_prompt(_classes("cup:"), ALL_KINDS)


def test_unchanged_references_are_reused_and_changed_ones_rebuilt() -> None:
    board: ReferenceBoard = ReferenceBoard()
    board.add(_box("cat"), _image())
    first: LabeledPrompt = board.build_prompt(_classes("cat", "dog"), ALL_KINDS)
    second: LabeledPrompt = board.build_prompt(_classes("dog", "cat"), ALL_KINDS)
    assert second.prompt.queries[2] == first.prompt.queries[1]
    board.add(_box("cat", left=30.0), _image())
    third: LabeledPrompt = board.build_prompt(_classes("cat"), ALL_KINDS)
    assert third.prompt.queries[1] != first.prompt.queries[1]


def test_boxes_follow_renames_and_removed_classes() -> None:
    board: ReferenceBoard = ReferenceBoard()
    board.add(_box("cat"), _image())
    board.add(_box("dog"), _image())
    board.rename_class("cat", "kitten")
    board.retain_classes(("kitten",))
    assert [box.class_name for box in board.boxes] == ["kitten"]


def test_reference_images_are_listed_and_removed_per_class() -> None:
    board: ReferenceBoard = ReferenceBoard()
    board.add(_box("cat", image_path=Path("b.jpg")), _image())
    board.add(_box("cat"), _image())
    board.add(_box("cat", image_path=Path("b.jpg"), left=20.0), _image())
    board.add(_box("dog"), _image())
    assert board.reference_images_of("cat") == (Path("b.jpg"), Path("a.jpg"))
    assert len(board.boxes_of("cat", Path("b.jpg"))) == 2
    board.remove_reference_image("cat", Path("b.jpg"))
    assert board.reference_images_of("cat") == (Path("a.jpg"),)
    board.clear()
    assert board.is_empty
