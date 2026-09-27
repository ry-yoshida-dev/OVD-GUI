from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from ovd_gui.gui.prompt import ReferenceSourceDialog


@pytest.fixture
def dialog(application: QApplication) -> ReferenceSourceDialog:
    return ReferenceSourceDialog()


def test_dropped_files_and_folders_become_reference_images(dialog: ReferenceSourceDialog, tmp_path: Path) -> None:
    folder: Path = tmp_path / "examples"
    folder.mkdir()
    Image.new("RGB", (8, 8)).save(folder / "b.png")
    Image.new("RGB", (8, 8)).save(folder / "a.png")
    (folder / "notes.txt").write_text("not an image")
    single_image: Path = tmp_path / "single.jpg"
    Image.new("RGB", (8, 8)).save(single_image)

    assert dialog.take_paths([single_image, folder])
    assert dialog.image_paths == (
        single_image.resolve(),
        (folder / "a.png").resolve(),
        (folder / "b.png").resolve(),
    )


def test_drop_without_supported_images_is_refused(dialog: ReferenceSourceDialog, tmp_path: Path) -> None:
    text_file: Path = tmp_path / "notes.txt"
    text_file.write_text("not an image")
    assert not dialog.take_paths([text_file, tmp_path])
    assert dialog.image_paths == ()
