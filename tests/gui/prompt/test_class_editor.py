from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QToolButton,
    QTreeWidgetItem,
)

from ovd_gui.detection import ReferenceBoard, ReferenceBox, ReferenceImage
from ovd_gui.gui.class_palette import ClassPalette
from ovd_gui.gui.prompt import ClassEditor, ClassSetDialog, ClassTree, ReferenceImageImporter
from ovd_gui.storage import ClassSetArchive, ClassSetStore
from ovd_gui.vocabulary import ClassDefinition, ClassListStore

EVENT_WAIT_MILLISECONDS = 20
_REFERENCE_IMAGE: ReferenceImage = ReferenceImage.of("a.jpg", Image.new("RGB", (10, 10)))
DropPosition = QAbstractItemView.DropIndicatorPosition


@pytest.fixture
def board() -> ReferenceBoard:
    return ReferenceBoard()


@pytest.fixture
def editor(application: QApplication, tmp_path: Path, board: ReferenceBoard) -> ClassEditor:
    data_directory: Path = tmp_path / "ovd_gui_data"
    class_editor: ClassEditor = ClassEditor(
        ClassPalette(), ClassListStore(data_directory), ClassSetStore(data_directory), board
    )
    class_editor.resize(320, 400)
    class_editor.show()
    return class_editor


def _open_row_editor(editor: ClassEditor) -> QLineEdit | None:
    line_edits: list[QLineEdit] = [
        line_edit for line_edit in _tree_of(editor).viewport().findChildren(QLineEdit) if line_edit.isVisible()
    ]
    return line_edits[0] if line_edits else None


def _enter(application: QApplication, editor: ClassEditor, text: str, key: Qt.Key = Qt.Key.Key_Return) -> None:
    line_edit: QLineEdit | None = _open_row_editor(editor)
    assert line_edit is not None
    QTest.keyClicks(line_edit, text)
    QTest.keyClick(line_edit, key)
    QTest.qWait(EVENT_WAIT_MILLISECONDS)


def _tree_of(editor: ClassEditor) -> ClassTree:
    tree: ClassTree | None = editor.findChild(ClassTree)
    assert tree is not None
    return tree


def _button_of(editor: ClassEditor, text: str) -> QToolButton:
    buttons: list[QToolButton] = [button for button in editor.findChildren(QToolButton) if button.text() == text]
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


def test_class_rows_show_id_and_query_count_with_phrases_as_children(editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.parse("car: car, suv, taxi"), ClassDefinition.named("dog")))
    assert _class_item(editor, 1).text(1) == "1"
    assert _class_item(editor, 0).text(2) == "3"
    assert _child_texts(editor, 0) == ["car", "suv", "taxi"]
    assert _child_texts(editor, 1) == ["dog"]


def test_editing_a_class_renames_it_and_its_named_phrase(editor: ClassEditor, board: ReferenceBoard) -> None:
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.named("dog")))
    board.add(ReferenceBox(_REFERENCE_IMAGE, "cat", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    _class_item(editor, 0).setText(0, "  kitten ")
    assert _texts(editor) == ["kitten", "dog"]
    assert _child_texts(editor, 0)[0] == "kitten"
    assert board.reference_images_of("kitten") == (_REFERENCE_IMAGE,)
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
    board.add(ReferenceBox(_REFERENCE_IMAGE, "dog", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    editor.refresh_references()
    assert _child_texts(editor, 1) == ["dog", "puppy", "a.jpg (1 box)"]
    tree: ClassTree = _tree_of(editor)
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
    board.add(ReferenceBox(_REFERENCE_IMAGE, "mug", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    editor.refresh_references()
    assert _class_item(editor, 0).text(2) == "1"
    editor.set_image_prompt_supported(False)
    assert _class_item(editor, 0).text(2) == "0"
    assert "Ignored" in _child_item(editor, 0, 0).toolTip(0)


def test_current_class_follows_the_current_row_or_its_parent(editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.parse("dog: dog, puppy")))
    assert editor.current_class_name is None
    _tree_of(editor).setCurrentItem(_child_item(editor, 1, 1))
    assert editor.current_class_name == "dog"


def test_named_class_set_round_trip_replaces_classes(editor: ClassEditor, tmp_path: Path) -> None:
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.parse("car: car, suv")))
    editor.save_class_set(" pets ")
    assert (tmp_path / "ovd_gui_data" / "classes" / "pets.ovdset").is_file()
    editor.set_classes((ClassDefinition.named("bird"),))
    editor.load_class_set("pets")
    assert _texts(editor) == ["cat", "car: car, suv"]


def test_class_set_restores_reference_images_without_their_files(
    editor: ClassEditor, board: ReferenceBoard, tmp_path: Path
) -> None:
    pixels: Image.Image = Image.new("RGB", (10, 10), (200, 30, 30))
    reference_image: ReferenceImage = ReferenceImage.of("sedan.jpg", pixels)
    editor.set_classes((ClassDefinition.parse("car: suv"), ClassDefinition.named("dog")))
    board.add(ReferenceBox(reference_image, "car", 1.0, 2.0, 8.0, 9.0), pixels)
    editor.save_class_set("vehicles")
    board.clear()
    editor.set_classes((ClassDefinition.named("bird"),))
    editor.load_class_set("vehicles")
    assert _texts(editor) == ["car: suv", "dog"]
    assert board.boxes == (ReferenceBox(reference_image, "car", 1.0, 2.0, 8.0, 9.0),)
    assert ReferenceImage.digest_of(board.pixels_of(reference_image)) == reference_image.digest
    assert _child_texts(editor, 0) == ["suv", "sedan.jpg (1 box)"]


def test_loading_a_class_set_replaces_the_reference_images(editor: ClassEditor, board: ReferenceBoard) -> None:
    editor.set_classes((ClassDefinition.named("cat"),))
    editor.save_class_set("plain")
    board.add(ReferenceBox(_REFERENCE_IMAGE, "cat", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    editor.load_class_set("plain")
    assert board.is_empty


def test_class_set_archive_file_replaces_classes(editor: ClassEditor, board: ReferenceBoard, tmp_path: Path) -> None:
    editor.set_classes((ClassDefinition.named("mug"),))
    board.add(ReferenceBox(_REFERENCE_IMAGE, "mug", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    editor.save_class_set("kitchen")
    shared_path: Path = tmp_path / "shared.ovdset"
    (tmp_path / "ovd_gui_data" / "classes" / "kitchen.ovdset").rename(shared_path)
    editor.clear()
    editor.load_file(shared_path)
    assert editor.class_names == ("mug",)
    assert board.reference_images_of("mug") == (_REFERENCE_IMAGE,)
    assert ClassSetArchive.is_archive_path(shared_path)


def test_text_file_replaces_classes(editor: ClassEditor, tmp_path: Path) -> None:
    path: Path = tmp_path / "coco.names"
    path.write_text("person\ncar\n", encoding="utf-8")
    editor.set_classes((ClassDefinition.named("bird"),))
    editor.load_file(path)
    assert editor.class_names == ("person", "car")


def test_loading_a_file_without_classes_keeps_classes(editor: ClassEditor, tmp_path: Path) -> None:
    path: Path = tmp_path / "empty.txt"
    path.write_text("\n\n", encoding="utf-8")
    editor.set_classes((ClassDefinition.named("cat"),))
    with pytest.raises(ValueError):
        editor.load_file(path)
    assert editor.class_names == ("cat",)


def test_plus_without_selection_appends_a_class(application: QApplication, editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.named("cat"),))
    _button_of(editor, "+ Text").click()
    _enter(application, editor, "  traffic   cone ")
    _tree_of(editor).clearSelection()
    _button_of(editor, "+ Text").click()
    _enter(application, editor, "car: car, suv")
    assert _texts(editor) == ["cat", "traffic cone", "car: car, suv"]
    assert _class_item(editor, 2).isExpanded()
    assert editor.current_class_name == "car"
    assert _open_row_editor(editor) is None


def test_plus_on_a_selected_class_inserts_a_class_after_it(application: QApplication, editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.named("dog")))
    _tree_of(editor).setCurrentItem(_class_item(editor, 0))
    _button_of(editor, "+ Text").click()
    assert _class_item(editor, 1).text(0) == ""
    _enter(application, editor, "bird")
    assert _texts(editor) == ["cat", "bird", "dog"]
    assert _class_item(editor, 2).text(1) == "2"


def test_plus_on_a_selected_query_inserts_a_phrase_after_it(application: QApplication, editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.parse("car: car, van"), ClassDefinition.named("bus")))
    _class_item(editor, 0).setExpanded(True)
    _tree_of(editor).setCurrentItem(_child_item(editor, 0, 0))
    _button_of(editor, "+ Text").click()
    assert _child_texts(editor, 0) == ["car", "", "van"]
    _enter(application, editor, "suv, taxi, CAR")
    assert _texts(editor) == ["car: car, suv, taxi, van", "bus"]
    assert _tree_of(editor).currentItem() is _child_item(editor, 0, 1)


def test_rejected_entry_is_reported_and_edited_again(application: QApplication, editor: ClassEditor) -> None:
    messages: list[str] = []
    editor.message_posted.connect(messages.append)
    editor.set_classes((ClassDefinition.parse("car: car, van"),))
    editor.start_new_row()
    _enter(application, editor, "van")
    assert messages == ["'van' is already a prompt of the class 'car'."]
    line_edit: QLineEdit | None = _open_row_editor(editor)
    assert line_edit is not None
    assert line_edit.text() == "van"
    QTest.keyClick(line_edit, Qt.Key.Key_Escape)
    QTest.qWait(EVENT_WAIT_MILLISECONDS)
    assert _texts(editor) == ["car: car, van"]
    assert _tree_of(editor).topLevelItemCount() == 1


def test_empty_or_cancelled_rows_are_dropped(application: QApplication, editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.named("cat"),))
    editor.start_new_row()
    _enter(application, editor, "  ")
    _tree_of(editor).setCurrentItem(_child_item(editor, 0, 0))
    editor.start_new_row()
    _enter(application, editor, "kitten", key=Qt.Key.Key_Escape)
    assert _texts(editor) == ["cat"]
    assert _child_texts(editor, 0) == ["cat"]


def test_dropping_a_phrase_on_another_class_moves_it(editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.parse("car: car, van"), ClassDefinition.named("truck")))
    tree: ClassTree = _tree_of(editor)
    tree.drop_query(_child_item(editor, 0, 1), _class_item(editor, 1), DropPosition.OnItem)
    assert _texts(editor) == ["car", "truck: truck, van"]
    assert tree.currentItem() is _child_item(editor, 1, 1)


def test_dropping_a_phrase_among_queries_reorders_it(editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.parse("car: car, suv, van"),))
    tree: ClassTree = _tree_of(editor)
    tree.drop_query(_child_item(editor, 0, 2), _child_item(editor, 0, 0), DropPosition.AboveItem)
    assert _texts(editor) == ["car: van, car, suv"]
    tree.drop_query(_child_item(editor, 0, 0), _child_item(editor, 0, 2), DropPosition.BelowItem)
    assert _texts(editor) == ["car: car, suv, van"]


def test_dropping_a_phrase_between_classes_makes_it_a_class(editor: ClassEditor) -> None:
    messages: list[str] = []
    editor.message_posted.connect(messages.append)
    editor.set_classes((ClassDefinition.parse("car: car, van"), ClassDefinition.named("truck")))
    tree: ClassTree = _tree_of(editor)
    tree.drop_query(_child_item(editor, 0, 1), _class_item(editor, 1), DropPosition.AboveItem)
    assert _texts(editor) == ["car", "van", "truck"]
    tree.drop_query(_child_item(editor, 2, 0), None, DropPosition.OnViewport)
    assert messages == ["A class named 'truck' already exists."]
    assert _texts(editor) == ["car", "van", "truck"]


def test_reference_images_move_between_classes_only(editor: ClassEditor, board: ReferenceBoard) -> None:
    messages: list[str] = []
    editor.message_posted.connect(messages.append)
    editor.set_classes((ClassDefinition.named("car"), ClassDefinition.named("truck")))
    board.add(ReferenceBox(_REFERENCE_IMAGE, "car", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    editor.refresh_references()
    tree: ClassTree = _tree_of(editor)
    tree.drop_query(_child_item(editor, 0, 1), None, DropPosition.OnViewport)
    assert messages == ["A reference image cannot become a class; drop it on a class instead."]
    tree.drop_query(_child_item(editor, 0, 1), _child_item(editor, 1, 0), DropPosition.BelowItem)
    assert board.reference_images_of("truck") == (_REFERENCE_IMAGE,)
    assert _child_texts(editor, 1) == ["truck", "a.jpg (1 box)"]


def test_double_click_below_the_rows_starts_a_new_class(application: QApplication, editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.named("cat"),))
    tree: ClassTree = _tree_of(editor)
    QTest.mouseDClick(tree.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(20, tree.viewport().height() - 5))
    _enter(application, editor, "dog")
    assert _texts(editor) == ["cat", "dog"]


def test_trash_button_removes_the_selected_rows(editor: ClassEditor) -> None:
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.parse("dog: dog, puppy")))
    remove_button: QToolButton = _button_of(editor, "Remove")
    assert not remove_button.isEnabled()
    _child_item(editor, 1, 1).setSelected(True)
    remove_button.click()
    assert _texts(editor) == ["cat", "dog"]


def test_image_action_adds_reference_images_to_the_current_class(
    editor: ClassEditor, board: ReferenceBoard, monkeypatch: pytest.MonkeyPatch
) -> None:
    requested_names: list[str] = []

    def import_one_image(importer: ReferenceImageImporter, class_name: str, class_names: tuple[str, ...]) -> int:
        requested_names.append(class_name)
        board.add(ReferenceBox(_REFERENCE_IMAGE, class_name, 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
        return 1

    monkeypatch.setattr(ReferenceImageImporter, "import_images", import_one_image)
    editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.named("dog")))
    messages: list[str] = []
    editor.message_posted.connect(messages.append)
    image_button: QToolButton = _button_of(editor, "+ Image")
    assert not image_button.isEnabled()
    _tree_of(editor).setCurrentItem(_class_item(editor, 1))
    image_button.click()
    assert requested_names == ["dog"]
    assert _child_texts(editor, 1) == ["dog", "a.jpg (1 box)"]
    assert messages == ["Added 1 reference image for 'dog'."]
    editor.set_image_prompt_supported(False)
    assert not image_button.isEnabled()


def test_class_set_library_loads_the_chosen_set(
    editor: ClassEditor, board: ReferenceBoard, monkeypatch: pytest.MonkeyPatch
) -> None:
    editor.set_classes((ClassDefinition.named("mug"),))
    board.add(ReferenceBox(_REFERENCE_IMAGE, "mug", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    editor.save_class_set("kitchen")
    editor.clear()
    asked_names: list[str] = []

    def choose_kitchen(dialog: ClassSetDialog, current_name: str) -> str | None:
        asked_names.append(current_name)
        return "kitchen"

    monkeypatch.setattr(ClassSetDialog, "ask", choose_kitchen)
    messages: list[str] = []
    editor.message_posted.connect(messages.append)
    editor._open_class_set_library()
    assert asked_names == ["kitchen"]
    assert editor.class_names == ("mug",)
    assert board.reference_images_of("mug") == (_REFERENCE_IMAGE,)
    assert messages == ["Loaded class set 'kitchen'."]


def _set_combo_of(editor: ClassEditor) -> QComboBox:
    combos: list[QComboBox] = editor.findChildren(QComboBox)
    assert len(combos) == 1
    return combos[0]


def test_set_drop_down_lists_saved_sets_and_loads_the_chosen_one(editor: ClassEditor) -> None:
    combo: QComboBox = _set_combo_of(editor)
    assert combo.count() == 0
    assert not combo.isEnabled()
    editor.set_classes((ClassDefinition.named("cat"),))
    editor.save_class_set("pets")
    editor.set_classes((ClassDefinition.named("car"),))
    editor.save_class_set("vehicles")
    assert [combo.itemText(index) for index in range(combo.count())] == ["pets", "vehicles"]
    assert combo.currentText() == "vehicles"
    combo.activated.emit(0)
    assert editor.class_names == ("cat",)
    assert editor.class_set_name == "pets"
    assert not editor.is_edited


def test_edits_are_marked_and_confirmed_before_switching_sets(
    editor: ClassEditor, monkeypatch: pytest.MonkeyPatch
) -> None:
    combo: QComboBox = _set_combo_of(editor)
    editor.set_classes((ClassDefinition.named("cat"),))
    editor.save_class_set("pets")
    editor.set_classes((ClassDefinition.named("car"),))
    editor.save_class_set("vehicles")
    edited_label: QLabel = next(label for label in editor.findChildren(QLabel) if label.text() == "Edited")
    assert edited_label.isHidden()
    editor.set_classes((ClassDefinition.named("car"), ClassDefinition.named("bus")))
    assert editor.is_edited
    assert not edited_label.isHidden()
    monkeypatch.setattr(QMessageBox, "question", lambda *arguments: QMessageBox.StandardButton.No)
    combo.activated.emit(0)
    assert editor.class_names == ("car", "bus")
    assert combo.currentText() == "vehicles"
    monkeypatch.setattr(QMessageBox, "question", lambda *arguments: QMessageBox.StandardButton.Yes)
    combo.activated.emit(0)
    assert editor.class_names == ("cat",)


def test_classes_from_a_file_are_not_tied_to_a_set(editor: ClassEditor, tmp_path: Path) -> None:
    editor.set_classes((ClassDefinition.named("cat"),))
    editor.save_class_set("pets")
    path: Path = tmp_path / "coco.names"
    path.write_text("person\n", encoding="utf-8")
    editor.load_file(path)
    assert editor.class_set_name == ""
    assert _set_combo_of(editor).currentIndex() == -1
