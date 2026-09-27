from pathlib import Path

import numpy as np
import pytest
from open_vocabulary_detector import DetectionResult, ImageSize, Prompt
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QTableView

from ovd_gui.detection import DetectionCatalog, DetectionRecord
from ovd_gui.gui.class_palette import ClassPalette
from ovd_gui.gui.table import AnalysisState, ClassFilterButton, ImageStatusRow, ResultColumn, ResultPanel


@pytest.fixture
def panel(application: QApplication) -> ResultPanel:
    result_panel: ResultPanel = ResultPanel(ClassPalette())
    result_panel.add_images([Path(name) for name in ("b.jpg", "a.jpg", "c.jpg", "d.jpg")])
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


def _statuses(panel: ResultPanel) -> list[tuple[str, AnalysisState]]:
    return [(row.image_path.name, row.state) for row in panel.visible_rows if isinstance(row, ImageStatusRow)]


def test_every_image_is_listed_and_undetected_images_say_so(panel: ResultPanel) -> None:
    assert _listed(panel) == [
        ("b.jpg", "cat", 0.3),
        ("b.jpg", "dog", 0.9),
        ("a.jpg", "cat", 0.7),
        ("c.jpg", "dog", 0.5),
        ("c.jpg", "dog", 0.6),
    ]
    assert _statuses(panel) == [("d.jpg", AnalysisState.NOT_ANALYZED)]
    table_view: QTableView = _table_view(panel)
    status_index = table_view.model().index(len(panel.visible_rows) - 1, ResultColumn.CLASS.value)
    assert status_index.data() == "Not analyzed"


def test_rows_of_the_current_image_are_highlighted(panel: ResultPanel) -> None:
    assert [row.image_path.name for row in panel.visible_rows if panel.is_current(row)] == ["b.jpg", "b.jpg"]
    table_view: QTableView = _table_view(panel)
    assert table_view.model().index(0, 0).data(Qt.ItemDataRole.BackgroundRole) is not None
    assert table_view.model().index(2, 0).data(Qt.ItemDataRole.BackgroundRole) is None
    panel.set_current_image(Path("d.jpg"))
    assert [row.image_path.name for row in panel.visible_rows if panel.is_current(row)] == ["d.jpg"]
    panel.set_current_image(None)
    assert not any(panel.is_current(row) for row in panel.visible_rows)


def test_class_filter_hides_images_without_detections(panel: ResultPanel) -> None:
    panel.set_class_filter({"dog"})
    assert _listed(panel) == [("b.jpg", "dog", 0.9), ("c.jpg", "dog", 0.5), ("c.jpg", "dog", 0.6)]
    assert _statuses(panel) == []


def test_funnel_button_filters_by_several_classes(panel: ResultPanel) -> None:
    button: ClassFilterButton | None = panel.findChild(ClassFilterButton)
    assert button is not None
    assert button.text() == "All classes"
    assert button.class_names == ("cat", "dog")
    panel.set_class_filter({"cat"})
    assert button.text() == "cat"
    assert _listed(panel) == [("b.jpg", "cat", 0.3), ("a.jpg", "cat", 0.7)]
    panel.set_class_filter({"cat", "dog"})
    assert button.text() == "cat, dog"
    assert len(_listed(panel)) == 5
    assert _statuses(panel) == []
    panel.set_class_filter(())
    assert _statuses(panel) == [("d.jpg", AnalysisState.NOT_ANALYZED)]


def test_sorting_by_confidence_and_image_name(panel: ResultPanel) -> None:
    table_view: QTableView = _table_view(panel)
    table_view.sortByColumn(ResultColumn.CONFIDENCE.value, Qt.SortOrder.DescendingOrder)
    assert [confidence for _, _, confidence in _listed(panel)] == [0.9, 0.7, 0.6, 0.5, 0.3]
    table_view.sortByColumn(ResultColumn.IMAGE.value, Qt.SortOrder.AscendingOrder)
    assert [image_name for image_name, _, _ in _listed(panel)] == ["a.jpg", "b.jpg", "b.jpg", "c.jpg", "c.jpg"]


def test_replacing_an_image_keeps_its_place_and_clearing_marks_images_not_analyzed(panel: ResultPanel) -> None:
    panel.replace_image(Path("b.jpg"), ())
    assert [row.image_path.name for row in panel.visible_rows] == ["b.jpg", "a.jpg", "c.jpg", "c.jpg", "d.jpg"]
    assert _statuses(panel) == [("b.jpg", AnalysisState.NO_DETECTIONS), ("d.jpg", AnalysisState.NOT_ANALYZED)]
    panel.set_class_filter({"dog"})
    panel.clear_results()
    assert _listed(panel) == []
    panel.set_class_filter(())
    assert _statuses(panel) == [(name, AnalysisState.NOT_ANALYZED) for name in ("b.jpg", "a.jpg", "c.jpg", "d.jpg")]
    with pytest.raises(KeyError):
        panel.set_class_filter({"bird"})


def test_selecting_a_row_reports_its_detection_or_image(panel: ResultPanel) -> None:
    table_view: QTableView = _table_view(panel)
    table_view.sortByColumn(ResultColumn.CONFIDENCE.value, Qt.SortOrder.DescendingOrder)
    selected: list[DetectionRecord] = []
    selected_images: list[Path] = []
    cleared: list[bool] = []
    panel.detection_selected.connect(selected.append)
    panel.image_selected.connect(selected_images.append)
    panel.selection_cleared.connect(lambda: cleared.append(True))
    table_view.selectRow(1)
    assert [(record.image_path, record.detection_index) for record in selected] == [(Path("a.jpg"), 0)]
    table_view.selectRow(5)
    assert selected_images == [Path("d.jpg")]
    table_view.clearSelection()
    assert cleared == [True]


def test_funnel_menu_toggles_classes(panel: ResultPanel) -> None:
    button: ClassFilterButton | None = panel.findChild(ClassFilterButton)
    assert button is not None
    menu: QMenu | None = button.menu()
    assert menu is not None
    menu.aboutToShow.emit()
    actions: dict[str, QAction] = {action.text(): action for action in menu.actions() if action.text()}
    actions["dog"].trigger()
    assert button.selected_class_names == frozenset({"dog"})
    menu.aboutToShow.emit()
    actions = {action.text(): action for action in menu.actions() if action.text()}
    actions["All classes"].trigger()
    assert button.selected_class_names == frozenset()
