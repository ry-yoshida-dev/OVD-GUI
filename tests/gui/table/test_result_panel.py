from pathlib import Path

import numpy as np
import pytest
from open_vocabulary_detector import DetectionResult, ImageSize, Prompt
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableView

from ovd_gui.detection import DetectionCatalog, DetectionRecord
from ovd_gui.gui.class_palette import ClassPalette
from ovd_gui.gui.table import ResultColumn, ResultPanel, ResultScope


@pytest.fixture
def panel(application: QApplication) -> ResultPanel:
    result_panel: ResultPanel = ResultPanel(ClassPalette())
    catalog: DetectionCatalog = DetectionCatalog()
    for image_name, class_ids, confidences in (
        ("b.jpg", [0, 1], [0.3, 0.9]),
        ("a.jpg", [0], [0.7]),
        ("c.jpg", [1, 1], [0.5, 0.6]),
    ):
        image_path: Path = Path(image_name)
        result: DetectionResult = DetectionResult.from_xyxy(
            xyxy=np.tile(np.array([0.0, 0.0, 10.0, 10.0]), (len(class_ids), 1)),
            confidences=np.array(confidences, dtype=np.float64),
            query_ids=np.array(class_ids, dtype=np.int64),
            prompt=Prompt.from_class_names(("cat", "dog")),
            image_size=ImageSize(width=100, height=50),
        )
        result_panel.replace_image(image_path, catalog.record(image_path, result, ("cat", "dog")))
    result_panel.set_current_image(Path("b.jpg"))
    return result_panel


def _listed(panel: ResultPanel) -> list[tuple[str, str, float]]:
    return [
        (record.image_path.name, record.detection.class_name, record.detection.confidence)
        for record in panel.visible_records
    ]


def _table_view(panel: ResultPanel) -> QTableView:
    table_view: QTableView | None = panel.findChild(QTableView)
    assert table_view is not None
    return table_view


def test_current_image_scope_lists_only_the_shown_image(panel: ResultPanel) -> None:
    assert panel.scope == ResultScope.CURRENT_IMAGE
    assert _listed(panel) == [("b.jpg", "cat", 0.3), ("b.jpg", "dog", 0.9)]


def test_all_images_scope_filtered_by_class(panel: ResultPanel) -> None:
    panel.set_scope(ResultScope.ALL_IMAGES)
    panel.set_class_filter("dog")
    assert _listed(panel) == [("b.jpg", "dog", 0.9), ("c.jpg", "dog", 0.5), ("c.jpg", "dog", 0.6)]


def test_sorting_by_confidence_and_image_name(panel: ResultPanel) -> None:
    panel.set_scope(ResultScope.ALL_IMAGES)
    table_view: QTableView = _table_view(panel)
    table_view.sortByColumn(ResultColumn.CONFIDENCE.value, Qt.SortOrder.DescendingOrder)
    assert [confidence for _, _, confidence in _listed(panel)] == [0.9, 0.7, 0.6, 0.5, 0.3]
    table_view.sortByColumn(ResultColumn.IMAGE.value, Qt.SortOrder.AscendingOrder)
    assert [image_name for image_name, _, _ in _listed(panel)] == ["a.jpg", "b.jpg", "b.jpg", "c.jpg", "c.jpg"]


def test_replacing_an_image_updates_rows_and_keeps_the_class_filter(panel: ResultPanel) -> None:
    panel.set_scope(ResultScope.ALL_IMAGES)
    panel.set_class_filter("dog")
    panel.replace_image(Path("c.jpg"), ())
    assert _listed(panel) == [("b.jpg", "dog", 0.9)]
    panel.clear()
    assert _listed(panel) == []
    with pytest.raises(KeyError):
        panel.set_class_filter("bird")


def test_selecting_a_row_reports_its_detection(panel: ResultPanel) -> None:
    panel.set_scope(ResultScope.ALL_IMAGES)
    table_view: QTableView = _table_view(panel)
    table_view.sortByColumn(ResultColumn.CONFIDENCE.value, Qt.SortOrder.DescendingOrder)
    selected: list[DetectionRecord] = []
    cleared: list[bool] = []
    panel.detection_selected.connect(selected.append)
    panel.selection_cleared.connect(lambda: cleared.append(True))
    table_view.selectRow(1)
    assert [(record.image_path, record.detection_index) for record in selected] == [(Path("a.jpg"), 0)]
    table_view.clearSelection()
    assert cleared == [True]
