from pathlib import Path

import pytest

from ovd_gui.storage import ClassSet, ClassSetEntry, ClassSetStore, ClassSetSummary
from ovd_gui.vocabulary import ClassDefinition


def test_class_sets_live_under_the_data_directory(tmp_path: Path) -> None:
    store: ClassSetStore = ClassSetStore(tmp_path / "ovd_gui_data")
    assert store.class_set_directory == tmp_path / "ovd_gui_data" / "classes"
    assert not store.class_set_names
    assert not store.class_set_directory.exists()


def test_class_sets_are_listed_by_name(tmp_path: Path) -> None:
    store: ClassSetStore = ClassSetStore(tmp_path / "ovd_gui_data")
    vehicles: tuple[ClassDefinition, ...] = (ClassDefinition.parse("car: car, suv"), ClassDefinition.named("truck"))
    store.write_class_set("vehicles", ClassSet(classes=vehicles))
    store.write_class_set("Animals", ClassSet(classes=(ClassDefinition.named("cat"),)))
    (store.class_set_directory / "old.txt").write_text("cat\n", encoding="utf-8")
    assert store.class_set_names == ("Animals", "vehicles")
    assert store.has_class_set("vehicles")
    assert store.read_class_set("vehicles").classes == vehicles


@pytest.mark.parametrize("name", ["", "   ", "../escape", "a/b", ".hidden", "what?"])
def test_unusable_class_set_names_are_rejected(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError):
        ClassSetStore(tmp_path / "ovd_gui_data").write_class_set(
            name, ClassSet(classes=(ClassDefinition.named("car"),))
        )


def _store_with(tmp_path: Path, *names: str) -> ClassSetStore:
    store: ClassSetStore = ClassSetStore(tmp_path / "ovd_gui_data")
    for name in names:
        store.write_class_set(
            name, ClassSet(classes=(ClassDefinition.parse("car: car, suv"), ClassDefinition.named(name)))
        )
    return store


def test_entries_summarise_sets_and_keep_unreadable_files(tmp_path: Path) -> None:
    store: ClassSetStore = _store_with(tmp_path, "vehicles")
    (store.class_set_directory / "broken.ovdset").write_text("not a zip", encoding="utf-8")
    entries: dict[str, ClassSetEntry] = {entry.name: entry for entry in store.entries}
    assert set(entries) == {"broken", "vehicles"}
    assert not entries["broken"].is_readable
    vehicles_summary: ClassSetSummary | None = entries["vehicles"].summary
    assert vehicles_summary is not None
    assert vehicles_summary.class_names == ("car", "vehicles")
    assert vehicles_summary.description == "2 classes · 3 text prompts"


def test_deleted_set_is_no_longer_listed(tmp_path: Path) -> None:
    store: ClassSetStore = _store_with(tmp_path, "a", "b")
    store.delete_class_set("a")
    assert store.class_set_names == ("b",)
    with pytest.raises(FileNotFoundError):
        store.delete_class_set("a")


def test_rename_refuses_to_overwrite_but_allows_a_case_change(tmp_path: Path) -> None:
    store: ClassSetStore = _store_with(tmp_path, "a", "b")
    with pytest.raises(FileExistsError):
        store.rename_class_set("a", "b")
    store.rename_class_set("a", "c")
    store.rename_class_set("c", "C")
    assert store.class_set_names == ("b", "C")
    with pytest.raises(FileNotFoundError):
        store.rename_class_set("missing", "d")


def test_exported_set_imports_under_a_new_name(tmp_path: Path) -> None:
    store: ClassSetStore = _store_with(tmp_path, "vehicles")
    shared_path: Path = tmp_path / "shared.ovdset"
    store.export_archive("vehicles", shared_path)
    store.import_archive(shared_path, "copy")
    assert store.read_class_set("copy").classes == store.read_class_set("vehicles").classes


def test_invalid_archive_is_not_imported(tmp_path: Path) -> None:
    store: ClassSetStore = ClassSetStore(tmp_path / "ovd_gui_data")
    broken_path: Path = tmp_path / "broken.ovdset"
    broken_path.write_text("not a zip", encoding="utf-8")
    with pytest.raises(ValueError):
        store.import_archive(broken_path, "broken")
    assert not store.class_set_names
