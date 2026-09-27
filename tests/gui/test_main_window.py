import time
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest
from open_vocabulary_detector import DetectionResult, DetectorBackend, ImageSize, OpenVocabularyDetector, Prompt
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableView

from ovd_gui.gui import MainWindow
from ovd_gui.gui.table import ResultColumn, ResultPanel, ResultScope
from ovd_gui.preset import PresetCatalog
from ovd_gui.vocabulary import ClassDefinition, ClassListStore


class WidthCountingDetector(OpenVocabularyDetector):
    BACKEND: ClassVar[DetectorBackend] = DetectorBackend.GROUNDING_DINO

    def _detect_mini_batch(self, images: Sequence[Image.Image], prompt: Prompt) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        for image in images:
            count: int = image.width // 32
            results.append(
                DetectionResult.from_xyxy(
                    xyxy=np.tile(np.array([1.0, 1.0, 20.0, 10.0]), (count, 1)),
                    confidences=np.linspace(0.3, 0.9, count),
                    query_ids=np.arange(count, dtype=np.int64) % len(prompt.queries),
                    prompt=prompt,
                    image_size=ImageSize(width=image.width, height=image.height),
                )
            )
        return results


@pytest.fixture
def window(application: QApplication, tmp_path: Path) -> Iterator[MainWindow]:
    image_directory: Path = tmp_path / "images"
    image_directory.mkdir()
    for index, width in enumerate((32, 64, 96)):
        Image.new("RGB", (width, 16)).save(image_directory / f"image{index}.png")
    main_window: MainWindow = MainWindow(PresetCatalog.from_package(), ClassListStore(tmp_path / "data"))
    main_window._class_editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.named("dog")))
    main_window.open_paths([image_directory])
    main_window._runner._worker._session._detector = WidthCountingDetector(
        main_window._settings_panel.current_settings()
    )
    yield main_window
    main_window.close()


def _wait_until_idle(application: QApplication, window: MainWindow) -> None:
    deadline: float = time.monotonic() + 10.0
    while window._runner.is_busy and time.monotonic() < deadline:
        application.processEvents()
    assert not window._runner.is_busy


def _child[WidgetType: ResultPanel | QTableView](window: MainWindow, widget_type: type[WidgetType]) -> WidgetType:
    widget: WidgetType | None = window.findChild(widget_type)
    assert widget is not None
    return widget


def test_detect_all_lists_every_image_and_opens_the_image_of_a_selected_row(
    application: QApplication, window: MainWindow
) -> None:
    window._detect_all()
    _wait_until_idle(application, window)
    panel: ResultPanel = _child(window, ResultPanel)
    assert panel.scope == ResultScope.ALL_IMAGES
    assert len(panel.visible_records) == 6

    panel.set_class_filter("dog")
    assert [(record.image_path.name, record.detection_index) for record in panel.visible_records] == [
        ("image1.png", 1),
        ("image2.png", 1),
    ]

    table_view: QTableView = _child(window, QTableView)
    table_view.sortByColumn(ResultColumn.CONFIDENCE.value, Qt.SortOrder.AscendingOrder)
    table_view.selectRow(0)
    assert window._current_image is not None
    assert window._current_image.path.name == "image2.png"
    assert window._image_list.currentRow() == 2


def test_stored_results_are_shown_again_and_can_be_cleared(application: QApplication, window: MainWindow) -> None:
    window._detect_all()
    _wait_until_idle(application, window)
    window._image_list.setCurrentRow(1)
    assert len(window._canvas._box_items) == 2
    window._clear_results()
    assert _child(window, ResultPanel).visible_records == ()
    window._image_list.setCurrentRow(2)
    assert window._canvas._box_items == []


def test_detections_are_reported_under_their_class_and_name_the_matched_query(
    application: QApplication, window: MainWindow
) -> None:
    window._class_editor.set_classes((ClassDefinition.parse("car: car, suv"), ClassDefinition.named("dog")))
    window._detect_all()
    _wait_until_idle(application, window)
    listed: set[tuple[str, str]] = {
        (record.detection.class_name, record.query_label) for record in _child(window, ResultPanel).visible_records
    }
    assert listed == {("car", "car"), ("car", "suv"), ("dog", "dog")}
