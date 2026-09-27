from pathlib import Path

from ovd_gui.vocabulary import ClassDefinition, ClassListStore


def test_nothing_is_remembered_initially(tmp_path: Path) -> None:
    store: ClassListStore = ClassListStore(tmp_path / "ovd_gui_data")
    assert store.load() is None
    assert not store.root_directory.exists()


def test_saved_classes_survive_a_new_store(tmp_path: Path) -> None:
    definitions: tuple[ClassDefinition, ...] = (ClassDefinition.named("person"), ClassDefinition.parse("car: suv"))
    ClassListStore(tmp_path / "ovd_gui_data").save(definitions)
    assert ClassListStore(tmp_path / "ovd_gui_data").load() == definitions


def test_unreadable_remembered_list_is_ignored(tmp_path: Path) -> None:
    store: ClassListStore = ClassListStore(tmp_path / "ovd_gui_data")
    store.root_directory.mkdir()
    (store.root_directory / ClassListStore.LAST_CLASSES_FILE_NAME).write_text("car: suv, suv\n", encoding="utf-8")
    assert store.load() is None


def test_empty_list_is_remembered_as_empty(tmp_path: Path) -> None:
    ClassListStore(tmp_path / "ovd_gui_data").save(())
    assert ClassListStore(tmp_path / "ovd_gui_data").load() == ()
