from open_vocabulary_detector import PromptKind
from PIL import Image

from ovd_gui.detection import PromptChange, PromptSignature, ReferenceBoard, ReferenceBox, ReferenceImage
from ovd_gui.vocabulary import ClassDefinition

ALL_KINDS: frozenset[PromptKind] = frozenset({PromptKind.TEXT, PromptKind.VISUAL})
TEXT_ONLY: frozenset[PromptKind] = frozenset({PromptKind.TEXT})
REFERENCE_PIXELS: Image.Image = Image.new("RGB", (100, 80))


def _signature(board: ReferenceBoard, *texts: str) -> PromptSignature:
    return board.signature_of(tuple(ClassDefinition.parse(text) for text in texts))


def _board_with_box(class_name: str) -> ReferenceBoard:
    board: ReferenceBoard = ReferenceBoard()
    board.add(
        ReferenceBox(
            reference_image=ReferenceImage.of("a.jpg", REFERENCE_PIXELS),
            class_name=class_name,
            left=10.0,
            top=10.0,
            right=50.0,
            bottom=40.0,
        ),
        REFERENCE_PIXELS,
    )
    return board


def test_same_classes_in_another_order_are_unchanged() -> None:
    board: ReferenceBoard = ReferenceBoard()
    change: PromptChange = PromptChange.between(
        _signature(board, "car: car, suv", "dog"), _signature(board, "dog", "car: suv, car")
    )
    assert change.is_unchanged
    assert change.description == ""


def test_added_removed_and_edited_classes_are_named() -> None:
    board: ReferenceBoard = ReferenceBoard()
    change: PromptChange = PromptChange.between(
        _signature(board, "car", "person", "dog"), _signature(board, "car", "dog: dog, puppy", "bus", "bike")
    )
    assert change == PromptChange(
        added_class_names=("bus", "bike"), removed_class_names=("person",), edited_class_names=("dog",)
    )
    assert not change.is_unchanged
    assert change.description == "added bus, bike · removed person · edited dog"


def test_reference_boxes_count_only_for_models_taking_image_prompts() -> None:
    recorded: PromptSignature = _signature(ReferenceBoard(), "car")
    current: PromptSignature = _signature(_board_with_box("car"), "car")
    assert PromptChange.between(recorded, current.for_prompt_kinds(ALL_KINDS)).edited_class_names == ("car",)
    assert PromptChange.between(recorded, current.for_prompt_kinds(TEXT_ONLY)).is_unchanged


def test_reference_only_classes_drop_out_for_text_only_models() -> None:
    board: ReferenceBoard = _board_with_box("mug")
    current: PromptSignature = _signature(board, "car", "mug:")
    assert [queried_class.name for queried_class in current.for_prompt_kinds(TEXT_ONLY).classes] == ["car"]
    assert [queried_class.name for queried_class in current.for_prompt_kinds(ALL_KINDS).classes] == ["car", "mug"]


def test_built_prompt_carries_the_signature_of_what_the_model_is_queried_with() -> None:
    board: ReferenceBoard = _board_with_box("car")
    definitions: tuple[ClassDefinition, ...] = (ClassDefinition.named("car"),)
    assert board.build_prompt(definitions, ALL_KINDS).signature == board.signature_of(definitions)
    assert board.build_prompt(definitions, TEXT_ONLY).signature == board.signature_of(definitions).for_prompt_kinds(
        TEXT_ONLY
    )
