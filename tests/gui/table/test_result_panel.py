from pathlib import Path

import numpy as np
import pytest
from open_vocabulary_detector import DetectionResult, ImageSize, Prompt
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QTableView

from ovd_gui.detection import DetectionCatalog, DetectionRecord
from ovd_gui.gui.class_palette import ClassPalette
from ovd_gui.gui.table import (
    AnalysisState,
    ColumnFilterPopup,
    FilterHeaderView,
    ImageStatusRow,
    RangeCondition,
    RangeEditor,
    ResultColumn,
    ResultPanel,
    ValueChecklist,
    ValueCondition,
)


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


def _filter_classes(panel: ResultPanel, *class_names: str) -> None:
    condition: ValueCondition | None = ValueCondition(frozenset(class_names)) if class_names else None
    panel.set_column_filter(ResultColumn.CLASS, condition)


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
    _filter_classes(panel, "dog")
    assert _listed(panel) == [("b.jpg", "dog", 0.9), ("c.jpg", "dog", 0.5), ("c.jpg", "dog", 0.6)]
    assert _statuses(panel) == []
    _filter_classes(panel, "cat", "Not analyzed")
    assert _listed(panel) == [("b.jpg", "cat", 0.3), ("a.jpg", "cat", 0.7)]
    assert _statuses(panel) == [("d.jpg", AnalysisState.NOT_ANALYZED)]
    _filter_classes(panel)
    assert len(_listed(panel)) == 5


def test_filters_of_several_columns_combine(panel: ResultPanel) -> None:
    panel.set_column_filter(ResultColumn.CONFIDENCE, RangeCondition(0.5, None))
    assert _listed(panel) == [
        ("b.jpg", "dog", 0.9),
        ("a.jpg", "cat", 0.7),
        ("c.jpg", "dog", 0.5),
        ("c.jpg", "dog", 0.6),
    ]
    assert _statuses(panel) == []
    panel.set_column_filter(ResultColumn.CONFIDENCE, RangeCondition(0.5, 0.7))
    panel.set_column_filter(ResultColumn.IMAGE, ValueCondition(frozenset({"c.jpg"})))
    assert _listed(panel) == [("c.jpg", "dog", 0.5), ("c.jpg", "dog", 0.6)]
    panel.set_column_filter(ResultColumn.X2, RangeCondition(None, 5.0))
    assert _listed(panel) == []
    assert set(panel.table_filter.conditions) == {ResultColumn.CONFIDENCE, ResultColumn.IMAGE, ResultColumn.X2}
    panel.clear_filters()
    assert panel.table_filter.is_empty
    assert len(panel.visible_rows) == 6


def test_condition_kind_must_suit_the_column(panel: ResultPanel) -> None:
    with pytest.raises(TypeError):
        panel.set_column_filter(ResultColumn.CONFIDENCE, ValueCondition(frozenset({"0.500"})))
    with pytest.raises(TypeError):
        panel.set_column_filter(ResultColumn.CLASS, RangeCondition(0.5, None))
    with pytest.raises(ValueError):
        RangeCondition(None, None)
    with pytest.raises(ValueError):
        RangeCondition(0.8, 0.2)


def test_header_funnel_shows_which_columns_are_filtered(panel: ResultPanel) -> None:
    model = _table_view(panel).model()
    unfiltered_icon = model.headerData(
        ResultColumn.CLASS.value, Qt.Orientation.Horizontal, Qt.ItemDataRole.DecorationRole
    )
    assert unfiltered_icon is not None
    _filter_classes(panel, "dog")
    tooltip = model.headerData(ResultColumn.CLASS.value, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole)
    assert tooltip == "Class: dog"
    filtered_icon = model.headerData(
        ResultColumn.CLASS.value, Qt.Orientation.Horizontal, Qt.ItemDataRole.DecorationRole
    )
    assert filtered_icon is not unfiltered_icon


def test_header_asks_for_the_filter_of_a_column(panel: ResultPanel) -> None:
    header: FilterHeaderView | None = panel.findChild(FilterHeaderView)
    assert header is not None
    requested: list[int] = []
    header.filter_requested.connect(lambda logical_index, _position: requested.append(logical_index))
    header.request_filter(ResultColumn.QUERY.value)
    assert requested == [ResultColumn.QUERY.value]
    with pytest.raises(IndexError):
        header.request_filter(len(ResultColumn))


def test_value_popup_checks_values_of_the_rows_passing_other_filters(panel: ResultPanel) -> None:
    panel.set_column_filter(ResultColumn.CONFIDENCE, RangeCondition(0.6, None))
    popup: ColumnFilterPopup = panel.open_filter_popup(ResultColumn.IMAGE, QPoint(0, 0))
    editor = popup.editor
    assert isinstance(editor, ValueChecklist)
    assert editor.condition is None
    editor.set_text_checked("a.jpg", False)
    popup.apply()
    assert panel.table_filter.condition_of(ResultColumn.IMAGE) == ValueCondition(frozenset({"b.jpg", "c.jpg"}))
    assert _listed(panel) == [("b.jpg", "dog", 0.9), ("c.jpg", "dog", 0.6)]

    popup = panel.open_filter_popup(ResultColumn.QUERY, QPoint(0, 0))
    editor = popup.editor
    assert isinstance(editor, ValueChecklist)
    editor.set_search_text("do")
    editor.set_matching_checked(False)
    popup.apply()
    assert panel.table_filter.condition_of(ResultColumn.QUERY) == ValueCondition(frozenset())
    assert _listed(panel) == []
    with pytest.raises(KeyError):
        panel.open_filter_popup(ResultColumn.QUERY, QPoint(0, 0)).editor.set_text_checked("cat", True)


def test_class_popup_offers_image_states(panel: ResultPanel) -> None:
    popup: ColumnFilterPopup = panel.open_filter_popup(ResultColumn.CLASS, QPoint(0, 0))
    editor = popup.editor
    assert isinstance(editor, ValueChecklist)
    editor.set_matching_checked(False)
    editor.set_text_checked("Not analyzed", True)
    popup.apply()
    assert _listed(panel) == []
    assert _statuses(panel) == [("d.jpg", AnalysisState.NOT_ANALYZED)]


def test_range_popup_edits_and_clears_bounds(panel: ResultPanel) -> None:
    popup: ColumnFilterPopup = panel.open_filter_popup(ResultColumn.CONFIDENCE, QPoint(0, 0))
    editor = popup.editor
    assert isinstance(editor, RangeEditor)
    assert editor.condition is None
    editor.set_minimum(0.55)
    popup.apply()
    assert panel.table_filter.condition_of(ResultColumn.CONFIDENCE) == RangeCondition(0.55, None)
    assert [confidence for _, _, confidence in _listed(panel)] == [0.9, 0.7, 0.6]

    popup = panel.open_filter_popup(ResultColumn.CONFIDENCE, QPoint(0, 0))
    editor = popup.editor
    assert isinstance(editor, RangeEditor)
    assert editor.condition == RangeCondition(0.55, None)
    editor.set_maximum(0.65)
    popup.apply()
    assert [confidence for _, _, confidence in _listed(panel)] == [0.6]

    panel.open_filter_popup(ResultColumn.CONFIDENCE, QPoint(0, 0)).clear()
    assert panel.table_filter.is_empty


def test_sorting_by_confidence_and_image_name(panel: ResultPanel) -> None:
    table_view: QTableView = _table_view(panel)
    table_view.sortByColumn(ResultColumn.CONFIDENCE.value, Qt.SortOrder.DescendingOrder)
    assert [confidence for _, _, confidence in _listed(panel)] == [0.9, 0.7, 0.6, 0.5, 0.3]
    table_view.sortByColumn(ResultColumn.IMAGE.value, Qt.SortOrder.AscendingOrder)
    assert [image_name for image_name, _, _ in _listed(panel)] == ["a.jpg", "b.jpg", "b.jpg", "c.jpg", "c.jpg"]


def test_replacing_an_image_keeps_its_place_and_showing_no_catalog_marks_images_not_analyzed(
    panel: ResultPanel,
) -> None:
    panel.replace_image(Path("b.jpg"), ())
    assert [row.image_path.name for row in panel.visible_rows] == ["b.jpg", "a.jpg", "c.jpg", "c.jpg", "d.jpg"]
    assert _statuses(panel) == [("b.jpg", AnalysisState.NO_DETECTIONS), ("d.jpg", AnalysisState.NOT_ANALYZED)]
    _filter_classes(panel, "dog")
    panel.show_catalog(None)
    assert _listed(panel) == []
    _filter_classes(panel)
    assert _statuses(panel) == [(name, AnalysisState.NOT_ANALYZED) for name in ("b.jpg", "a.jpg", "c.jpg", "d.jpg")]


def test_showing_a_catalog_lists_its_results_in_image_order(panel: ResultPanel) -> None:
    catalog: DetectionCatalog = DetectionCatalog()
    result: DetectionResult = DetectionResult.from_xyxy(
        xyxy=np.array([[0.0, 0.0, 10.0, 10.0]]),
        confidences=np.array([0.8]),
        query_ids=np.array([1], dtype=np.int64),
        prompt=Prompt.from_class_names(("cat", "dog")),
        image_size=ImageSize(width=100, height=50),
    )
    catalog.record(Path("c.jpg"), result, ("cat", "dog"))
    catalog.record(Path("a.jpg"), result.filter_by_confidence(0.9), ("cat", "dog"))
    panel.show_catalog(catalog)
    assert _listed(panel) == [("c.jpg", "dog", 0.8)]
    assert _statuses(panel) == [
        ("b.jpg", AnalysisState.NOT_ANALYZED),
        ("a.jpg", AnalysisState.NO_DETECTIONS),
        ("d.jpg", AnalysisState.NOT_ANALYZED),
    ]


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
