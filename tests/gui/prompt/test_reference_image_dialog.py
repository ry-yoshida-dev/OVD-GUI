from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QApplication

from ovd_gui.detection import ReferenceBox
from ovd_gui.gui.class_palette import ClassPalette
from ovd_gui.gui.prompt import ReferenceImageDialog
from ovd_gui.gui.viewer import ImageCanvas
from ovd_gui.media import LoadedImage


@pytest.fixture
def dialog(application: QApplication) -> ReferenceImageDialog:
    reference_dialog: ReferenceImageDialog = ReferenceImageDialog(ClassPalette())
    loaded_image: LoadedImage = LoadedImage(path=Path("example.png"), image=Image.new("RGB", (120, 80)))
    reference_dialog.set_reference_image(loaded_image, "dog", ("cat", "dog"))
    return reference_dialog


def _canvas_of(dialog: ReferenceImageDialog) -> ImageCanvas:
    canvas: ImageCanvas | None = dialog.findChild(ImageCanvas)
    assert canvas is not None
    return canvas


def test_without_boxes_the_whole_image_is_the_reference(dialog: ReferenceImageDialog) -> None:
    assert dialog.boxes == (
        ReferenceBox(image_path=Path("example.png"), class_name="dog", left=0.0, top=0.0, right=120.0, bottom=80.0),
    )


def test_drawn_boxes_replace_the_whole_image(dialog: ReferenceImageDialog) -> None:
    canvas: ImageCanvas = _canvas_of(dialog)
    canvas.rectangle_drawn.emit(QRectF(10.0, 20.0, 30.0, 40.0))
    canvas.rectangle_drawn.emit(QRectF(50.0, 5.0, 20.0, 20.0))
    assert [box.xyxy for box in dialog.boxes] == [(10.0, 20.0, 40.0, 60.0), (50.0, 5.0, 70.0, 25.0)]
    assert all(box.class_name == "dog" for box in dialog.boxes)


def test_a_new_image_starts_without_boxes(dialog: ReferenceImageDialog) -> None:
    _canvas_of(dialog).rectangle_drawn.emit(QRectF(10.0, 20.0, 30.0, 40.0))
    other_image: LoadedImage = LoadedImage(path=Path("other.png"), image=Image.new("RGB", (50, 50)))
    dialog.set_reference_image(other_image, "cat", ("cat", "dog"))
    assert [box.xyxy for box in dialog.boxes] == [(0.0, 0.0, 50.0, 50.0)]
