from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ovd_gui.detection import ReferenceBox
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


def _show_editable_box(canvas: ImageCanvas) -> list[tuple[int, QRectF]]:
    adjustments: list[tuple[int, QRectF]] = []
    canvas.reference_adjusted.connect(lambda index, rectangle: adjustments.append((index, rectangle)))
    canvas.set_drawing_enabled(True)
    canvas.show_references(
        [ReferenceBox(image_path=Path("a.png"), class_name="dog", left=40.0, top=20.0, right=80.0, bottom=60.0)],
        ("dog",),
    )
    return adjustments


def test_dragging_a_corner_handle_resizes_the_box(canvas: ImageCanvas) -> None:
    adjustments: list[tuple[int, QRectF]] = _show_editable_box(canvas)
    rectangles: list[QRectF] = []
    canvas.rectangle_drawn.connect(rectangles.append)
    _drag(canvas, canvas.mapFromScene(80.0, 60.0), canvas.mapFromScene(120.0, 90.0))
    assert rectangles == []
    assert len(adjustments) == 1
    index, rectangle = adjustments[0]
    assert index == 0
    assert (rectangle.left(), rectangle.top()) == (40.0, 20.0)
    assert rectangle.right() == pytest.approx(120.0, abs=1.0)
    assert rectangle.bottom() == pytest.approx(90.0, abs=1.0)


def test_dragging_inside_the_box_moves_it_within_the_image(canvas: ImageCanvas) -> None:
    adjustments: list[tuple[int, QRectF]] = _show_editable_box(canvas)
    _drag(canvas, canvas.mapFromScene(60.0, 40.0), canvas.mapFromScene(190.0, 45.0))
    assert len(adjustments) == 1
    rectangle: QRectF = adjustments[0][1]
    assert rectangle.right() == pytest.approx(200.0)
    assert rectangle.width() == pytest.approx(40.0)
    assert rectangle.top() == pytest.approx(25.0, abs=1.0)


def test_dragging_outside_the_box_draws_a_new_one(canvas: ImageCanvas) -> None:
    adjustments: list[tuple[int, QRectF]] = _show_editable_box(canvas)
    rectangles: list[QRectF] = []
    canvas.rectangle_drawn.connect(rectangles.append)
    _drag(canvas, canvas.mapFromScene(120.0, 20.0), canvas.mapFromScene(180.0, 80.0))
    assert adjustments == []
    assert len(rectangles) == 1
