import pytest
from PIL import Image
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ovd_gui.gui.class_palette import ClassPalette
from ovd_gui.gui.viewer import ImageCanvas


@pytest.fixture
def canvas(application: QApplication) -> ImageCanvas:
    view: ImageCanvas = ImageCanvas(ClassPalette())
    view.resize(400, 300)
    view.set_image(Image.new("RGB", (200, 100), "gray"))
    view.show()
    view.fit_to_view()
    return view


def _drag(canvas: ImageCanvas, start: QPoint, end: QPoint) -> None:
    viewport = canvas.viewport()
    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(viewport, end)
    QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)


def test_drawing_emits_a_rectangle_clamped_to_the_image(canvas: ImageCanvas) -> None:
    rectangles: list[QRectF] = []
    canvas.rectangle_drawn.connect(rectangles.append)
    canvas.set_drawing_enabled(True)
    canvas.scale(0.5, 0.5)
    top_left: QPoint = canvas.mapFromScene(20.0, 10.0)
    _drag(canvas, top_left, QPoint(canvas.viewport().width() - 1, canvas.viewport().height() - 1))
    assert len(rectangles) == 1
    assert rectangles[0].left() == pytest.approx(20.0, abs=2.0)
    assert rectangles[0].right() == pytest.approx(200.0)
    assert rectangles[0].bottom() == pytest.approx(100.0)


def test_dragging_without_drawing_mode_emits_nothing(canvas: ImageCanvas) -> None:
    rectangles: list[QRectF] = []
    canvas.rectangle_drawn.connect(rectangles.append)
    _drag(canvas, canvas.mapFromScene(20.0, 10.0), canvas.mapFromScene(120.0, 80.0))
    assert rectangles == []
