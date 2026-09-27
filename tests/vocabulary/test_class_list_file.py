from pathlib import Path

import pytest

from ovd_gui.vocabulary import ClassDefinition, ClassListFile


def test_written_classes_are_read_back_in_order(tmp_path: Path) -> None:
    class_list_file: ClassListFile = ClassListFile(tmp_path / "classes.txt")
    definitions: tuple[ClassDefinition, ...] = (
        ClassDefinition.named("person"),
        ClassDefinition.parse("car: car, suv, taxi"),
        ClassDefinition.parse("my mug:"),
    )
    class_list_file.write(definitions)
    assert class_list_file.path.read_text(encoding="utf-8") == "person\ncar: car, suv, taxi\nmy mug:\n"
    assert class_list_file.read() == definitions


def test_plain_name_lists_are_read_as_named_classes(tmp_path: Path) -> None:
    path: Path = tmp_path / "coco.names"
    path.write_text("  person \n\n\tcar\r\n   \n", encoding="utf-8")
    assert ClassListFile(path).read() == (ClassDefinition.named("person"), ClassDefinition.named("car"))


def test_invalid_line_is_rejected(tmp_path: Path) -> None:
    path: Path = tmp_path / "classes.txt"
    path.write_text("car: suv, SUV\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ClassListFile(path).read()
