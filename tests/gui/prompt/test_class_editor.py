from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem

from ovd_gui.detection import ReferenceBoard, ReferenceBox
from ovd_gui.gui.class_palette import ClassPalette
from ovd_gui.gui.prompt import ClassEditor, ReferenceImageImporter
from ovd_gui.vocabulary import ClassDefinition, ClassListFile, ClassListStore


@pytest.fixture
def board() -> ReferenceBoard:
    return ReferenceBoard()


@pytest.fixture
def editor(application: QApplication, tmp_path: Path, board: ReferenceBoard) -> ClassEditor:
    return ClassEditor(ClassPalette(), ClassListStore(tmp_path / "ovd_gui_data"), board)


def _input_of(editor: ClassEditor) -> QLineEdit:
    input_edit: QLineEdit | None = editor.findChild(QLineEdit)
    assert input_edit is not None
    return input_edit


def _tree_of(editor: ClassEditor) -> QTreeWidget:
    tree: QTreeWidget | None = editor.findChild(QTreeWidget)
    assert tree is not None
    return tree


def _button_of(editor: ClassEditor, text: str) -> QPushButton:
    buttons: list[QPushButton] = [button for button in editor.findChildren(QPushButton) if button.text() == text]
    assert len(buttons) == 1
    return buttons[0]


def _class_item(editor: ClassEditor, class_index: int) -> QTreeWidgetItem:
    item: QTreeWidgetItem | None = _tree_of(editor).topLevelItem(class_index)
    assert item is not None
    return item


def _child_item(editor: ClassEditor, class_index: int, child_index: int) -> QTreeWidgetItem:
    item: QTreeWidgetItem | None = _class_item(editor, class_index).child(child_index)
    assert item is not None
    return item


def _child_texts(editor: ClassEditor, class_index: int) -> list[str]:
    class_item: QTreeWidgetItem = _class_item(editor, class_index)
    return [_child_item(editor, class_index, index).text(0) for index in range(class_item.childCount())]


def _texts(editor: ClassEditor) -> list[str]:
    return [definition.text for definition in editor.classes]


def _type(editor: ClassEditor, text: str) -> None:
    input_edit: QLineEdit = _input_of(editor)
    QTest.keyClicks(input_edit, text)
    QTest.keyClick(input_edit, Qt.Key.Key_Return)


def test_class_rows_show_id_and_query_count_with_phrases_as_children(editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.parse("car: car, suv, taxi"), ClassDefinition.named("dog")))
    assert _class_item(editor, 1).text(1) == "1"
    assert _class_item(editor, 0).text(2) == "3"
    assert _child_texts(editor, 0) == ["car", "suv", "taxi"]
    assert _child_texts(editor, 1) == ["dog"]


def test_enter_adds_named_classes_or_one_class_with_phrases(editor: ClassEditor) -> None:
    _type(editor, "cat, traffic cone")
    _type(editor, "car: car, suv")
    _type(editor, "CAR: taxi")
    assert _texts(editor) == ["cat", "traffic cone", "car: car, suv, taxi"]
    assert _input_of(editor).text() == ""
    assert _class_item(editor, 2).isExpanded()


def test_input_reusing_a_phrase_of_another_class_is_kept_with_a_notice(editor: ClassEditor) -> None:
    messages: list[str] = []
    editor.message_posted.connect(messages.append)
    _type(editor, "car: car, van")
    _type(editor, "van")
    assert _texts(editor) == ["car: car, van"]
    assert _input_of(editor).text() == "van"
    assert messages == ["'van' already queries the class 'car'."]


def test_editing_a_class_renames_it_and_its_named_phrase(editor: ClassEditor, board: ReferenceBoard) -> None:
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.named("dog")))
    board.add(ReferenceBox(Path("a.jpg"), "cat", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    _class_item(editor, 0).setText(0, "  kitten ")
    assert _texts(editor) == ["kitten", "dog"]
    assert _child_texts(editor, 0)[0] == "kitten"
    assert board.reference_images_of("kitten") == (Path("a.jpg"),)
    _class_item(editor, 0).setText(0, "DOG")
    assert _texts(editor) == ["kitten", "dog"]
    assert _class_item(editor, 0).text(0) == "kitten"


def test_editing_a_phrase_is_applied_or_reverted(editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.parse("car: car, suv"), ClassDefinition.named("dog")))
    _child_item(editor, 0, 1).setText(0, "van")
    assert _texts(editor) == ["car: car, van", "dog"]
    _child_item(editor, 0, 1).setText(0, "Dog")
    assert _texts(editor) == ["car: car, van", "dog"]
    assert _child_item(editor, 0, 1).text(0) == "van"


def test_delete_removes_selected_classes_phrases_and_reference_images(
    editor: ClassEditor, board: ReferenceBoard
) -> None:
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.parse("dog: dog, puppy")))
    board.add(ReferenceBox(Path("a.jpg"), "dog", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    editor.refresh_references()
    assert _child_texts(editor, 1) == ["dog", "puppy", "a.jpg (1 box)"]
    tree: QTreeWidget = _tree_of(editor)
    _child_item(editor, 1, 0).setSelected(True)
    _child_item(editor, 1, 2).setSelected(True)
    QTest.keyClick(tree, Qt.Key.Key_Delete)
    assert _texts(editor) == ["cat", "dog: puppy"]
    assert board.is_empty
    _class_item(editor, 0).setSelected(True)
    QTest.keyClick(tree, Qt.Key.Key_Delete)
    assert _texts(editor) == ["dog: puppy"]
    assert _class_item(editor, 0).text(1) == "0"


def test_reference_images_are_greyed_out_without_image_prompt_support(
    editor: ClassEditor, board: ReferenceBoard
) -> None:
    editor.set_classes((ClassDefinition.parse("mug:"),))
    board.add(ReferenceBox(Path("a.jpg"), "mug", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    editor.refresh_references()
    assert _class_item(editor, 0).text(2) == "1"
    editor.set_image_prompt_supported(False)
    assert _class_item(editor, 0).text(2) == "0"
    assert "Ignored" in _child_item(editor, 0, 0).toolTip(0)


def test_enter_on_empty_input_requests_detection(editor: ClassEditor) -> None:
    requests: list[bool] = []
    editor.detection_requested.connect(lambda: requests.append(True))
    QTest.keyClick(_input_of(editor), Qt.Key.Key_Return)
    assert requests == [True]


def test_current_class_follows_the_current_row_or_its_parent(editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.parse("dog: dog, puppy")))
    assert editor.current_class_name is None
    _tree_of(editor).setCurrentItem(_child_item(editor, 1, 1))
    assert editor.current_class_name == "dog"


def test_add_phrases_extends_a_class(editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.named("car"), ClassDefinition.named("bus")))
    editor.add_phrases("car", "suv, taxi, CAR")
    assert _texts(editor) == ["car: car, suv, taxi", "bus"]
    with pytest.raises(ValueError):
        editor.add_phrases("car", "bus")
    with pytest.raises(KeyError):
        editor.add_phrases("truck", "lorry")


def test_named_class_set_round_trip_replaces_classes(editor: ClassEditor, tmp_path: Path) -> None:
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.parse("car: car, suv")))
    editor.save_class_set(" pets ")
    saved_path: Path = tmp_path / "ovd_gui_data" / "classes" / "pets.txt"
    assert saved_path.read_text(encoding="utf-8") == "cat\ncar: car, suv\n"
    editor.set_classes((ClassDefinition.named("bird"),))
    editor.load_class_set("pets")
    assert _texts(editor) == ["cat", "car: car, suv"]


def test_text_file_replaces_classes(editor: ClassEditor, tmp_path: Path) -> None:
    path: Path = tmp_path / "coco.names"
    path.write_text("person\ncar\n", encoding="utf-8")
    editor.set_classes((ClassDefinition.named("bird"),))
    editor.load_file(ClassListFile(path))
    assert editor.class_names == ("person", "car")


def test_loading_a_file_without_classes_keeps_classes(editor: ClassEditor, tmp_path: Path) -> None:
    path: Path = tmp_path / "empty.txt"
    path.write_text("\n\n", encoding="utf-8")
    editor.set_classes((ClassDefinition.named("cat"),))
    with pytest.raises(ValueError):
        editor.load_file(ClassListFile(path))
    assert editor.class_names == ("cat",)


def test_query_buttons_act_on_the_current_class(
    editor: ClassEditor, board: ReferenceBoard, monkeypatch: pytest.MonkeyPatch
) -> None:
    requested_names: list[str] = []

    def import_one_image(importer: ReferenceImageImporter, class_name: str, class_names: tuple[str, ...]) -> int:
        requested_names.append(class_name)
        board.add(ReferenceBox(Path("a.jpg"), class_name, 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
        return 1

    monkeypatch.setattr(ReferenceImageImporter, "import_images", import_one_image)
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.named("dog")))
    messages: list[str] = []
    editor.message_posted.connect(messages.append)
    reference_button: QPushButton = _button_of(editor, "Add Images...")
    phrase_button: QPushButton = _button_of(editor, "Add Phrases...")
    assert not reference_button.isEnabled()
    assert not phrase_button.isEnabled()
    _tree_of(editor).setCurrentItem(_class_item(editor, 1))
    assert phrase_button.isEnabled()
    reference_button.click()
    assert requested_names == ["dog"]
    assert _child_texts(editor, 1) == ["dog", "a.jpg (1 box)"]
    assert messages == ["Added 1 reference image for 'dog'."]
    editor.set_image_prompt_supported(False)
    assert not reference_button.isEnabled()
