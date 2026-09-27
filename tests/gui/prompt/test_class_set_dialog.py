from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from ovd_gui.detection import ReferenceBoard, ReferenceBox, ReferenceImage
from ovd_gui.gui.class_palette import ClassPalette
from ovd_gui.gui.prompt import ClassSetDialog
from ovd_gui.storage import ClassSet, ClassSetStore
from ovd_gui.vocabulary import ClassDefinition


@pytest.fixture
def store(tmp_path: Path) -> ClassSetStore:
    class_set_store: ClassSetStore = ClassSetStore(tmp_path / "ovd_gui_data")
    pixels: Image.Image = Image.new("RGB", (40, 30), (10, 120, 200))
    reference_image: ReferenceImage = ReferenceImage.of("sedan.jpg", pixels)
    board: ReferenceBoard = ReferenceBoard()
    board.add(ReferenceBox(reference_image, "car", 2.0, 2.0, 30.0, 20.0), pixels)
    class_set_store.write_class_set(
        "vehicles", ClassSet.of((ClassDefinition.parse("car: car, suv"), ClassDefinition.named("truck")), board)
    )
    class_set_store.write_class_set(
        "animals", ClassSet(classes=(ClassDefinition.named("cat"), ClassDefinition.named("zebra")))
    )
    return class_set_store


@pytest.fixture
def dialog(application: QApplication, store: ClassSetStore) -> ClassSetDialog:
    class_set_dialog: ClassSetDialog = ClassSetDialog(store, ClassPalette())
    class_set_dialog.open_library("vehicles")
    return class_set_dialog


def _load_button_of(dialog: ClassSetDialog) -> QPushButton:
    buttons: list[QPushButton] = [button for button in dialog.findChildren(QPushButton) if button.text() == "Load"]
    assert len(buttons) == 1
    return buttons[0]


def test_sets_are_listed_and_the_current_one_previewed(dialog: ClassSetDialog) -> None:
    assert dialog.listed_names == ("animals", "vehicles")
    assert dialog.current_name == "vehicles"
    assert dialog.preview.is_showing_content
    assert dialog.preview.class_texts == ("car: car, suv", "truck: truck")
    assert dialog.preview.thumbnail_count == 1


def test_search_matches_set_and_class_names(dialog: ClassSetDialog) -> None:
    dialog._search_edit.setText("ZEB")
    assert dialog.listed_names == ("animals",)
    assert dialog.current_name == "animals"
    dialog._search_edit.setText("nothing")
    assert list(dialog.listed_names) == []
    assert not _load_button_of(dialog).isEnabled()


def test_load_closes_with_the_current_set(dialog: ClassSetDialog) -> None:
    _load_button_of(dialog).click()
    assert dialog.chosen_name == "vehicles"
    assert dialog.result() == ClassSetDialog.DialogCode.Accepted


def test_deleting_selects_the_next_set(dialog: ClassSetDialog, store: ClassSetStore) -> None:
    dialog.delete_class_set("animals")
    assert store.class_set_names == ("vehicles",)
    assert dialog.listed_names == ("vehicles",)
    assert dialog.current_name == "vehicles"
    dialog.delete_class_set("vehicles")
    assert list(dialog.listed_names) == []
    assert not dialog.preview.is_showing_content


def test_delete_asks_for_confirmation(
    dialog: ClassSetDialog, store: ClassSetStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(QMessageBox, "exec", lambda _box: 0)
    dialog._delete_current()
    assert store.class_set_names == ("animals", "vehicles")


def test_renaming_in_place_renames_the_file(dialog: ClassSetDialog, store: ClassSetStore) -> None:
    item = dialog._list.currentItem()
    item.setText("  cars ")
    assert store.class_set_names == ("animals", "cars")
    assert dialog.current_name == "cars"


def test_rename_onto_another_set_is_refused(
    dialog: ClassSetDialog, store: ClassSetStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *arguments: warnings.append(str(arguments[2])))
    dialog._list.currentItem().setText("animals")
    assert store.class_set_names == ("animals", "vehicles")
    assert dialog._list.currentItem().text() == "vehicles"
    assert warnings == ["A class set named 'animals' already exists."]


def test_unreadable_set_can_only_be_renamed_or_deleted(dialog: ClassSetDialog, store: ClassSetStore) -> None:
    (store.class_set_directory / "broken.ovdset").write_text("not a zip", encoding="utf-8")
    dialog.open_library("broken")
    assert dialog.current_name == "broken"
    assert not dialog.preview.is_showing_content
    assert not _load_button_of(dialog).isEnabled()
    dialog.delete_class_set("broken")
    assert store.class_set_names == ("animals", "vehicles")
