import csv
from pathlib import Path

import numpy as np
import pytest
from open_vocabulary_detector import DetectionResult, ImageSize, Prompt, PromptKind
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QHeaderView, QLabel, QMenu, QPushButton, QTableView, QToolButton

from ovd_gui.detection import DetectionCatalog, DetectionRecord, LabeledPrompt, PromptChange, ReferenceBoard
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
from ovd_gui.review import ClassThresholds
from ovd_gui.vocabulary import ClassDefinition

CAT_DOG_PROMPT: LabeledPrompt = ReferenceBoard().build_prompt(
    (ClassDefinition.named("cat"), ClassDefinition.named("dog")), frozenset({PromptKind.TEXT})
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
        result_panel.replace_image(image_path, catalog.record(image_path, result, CAT_DOG_PROMPT))
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


def _selected_image(panel: ResultPanel) -> Path | None:
    table_view: QTableView = _table_view(panel)
    selected_rows: list[int] = [index.row() for index in table_view.selectionModel().selectedRows()]
    return panel.visible_rows[selected_rows[0]].image_path if selected_rows else None


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


def test_only_filtered_headers_carry_a_funnel(panel: ResultPanel) -> None:
    model = _table_view(panel).model()
    assert model.headerData(ResultColumn.CLASS.value, Qt.Orientation.Horizontal, Qt.ItemDataRole.DecorationRole) is None
    _filter_classes(panel, "dog")
    tooltip = model.headerData(ResultColumn.CLASS.value, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole)
    assert tooltip == "Class: dog"
    assert (
        model.headerData(ResultColumn.CLASS.value, Qt.Orientation.Horizontal, Qt.ItemDataRole.DecorationRole)
        is not None
    )
    assert model.headerData(ResultColumn.QUERY.value, Qt.Orientation.Horizontal, Qt.ItemDataRole.DecorationRole) is None


def test_one_filter_button_lists_every_column(panel: ResultPanel) -> None:
    _filter_classes(panel, "dog")
    button: QToolButton | None = panel.findChild(QToolButton)
    assert button is not None
    menu: QMenu | None = button.menu()
    assert menu is not None
    panel._fill_filter_menu()
    column_actions: list[QAction] = [action for action in menu.actions() if action.isCheckable()]
    assert len(column_actions) == len(ResultColumn)
    assert [action.isChecked() for action in column_actions] == [
        column == ResultColumn.CLASS for column in ResultColumn
    ]
    column_actions[ResultColumn.QUERY.value].trigger()
    popup: ColumnFilterPopup | None = panel.findChild(ColumnFilterPopup)
    assert popup is not None
    popup.close()


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
    reopened_editor = panel.open_filter_popup(ResultColumn.QUERY, QPoint(0, 0)).editor
    assert isinstance(reopened_editor, ValueChecklist)
    with pytest.raises(KeyError):
        reopened_editor.set_text_checked("cat", True)


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
    catalog.record(Path("c.jpg"), result, CAT_DOG_PROMPT)
    catalog.record(Path("a.jpg"), result.filter_by_confidence(0.9), CAT_DOG_PROMPT)
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


def test_updating_rows_never_moves_the_selection_to_another_image(panel: ResultPanel) -> None:
    table_view: QTableView = _table_view(panel)
    table_view.selectRow(2)
    reported_images: list[Path] = []
    cleared: list[bool] = []
    panel.detection_selected.connect(lambda record: reported_images.append(record.image_path))
    panel.image_selected.connect(reported_images.append)
    panel.selection_cleared.connect(lambda: cleared.append(True))

    panel.replace_image(Path("b.jpg"), ())
    assert _selected_image(panel) == Path("a.jpg")
    assert cleared == []

    panel.replace_image(Path("a.jpg"), ())
    assert _selected_image(panel) is None
    assert cleared == [True]

    table_view.selectRow(3)
    reported_images.clear()
    _filter_classes(panel, "cat")
    assert _selected_image(panel) is None
    assert cleared == [True, True]
    assert reported_images == []


def test_outdated_images_are_marked_and_can_be_updated(panel: ResultPanel) -> None:
    update_requests: list[bool] = []
    panel.update_outdated_requested.connect(lambda: update_requests.append(True))
    update_button: QPushButton = next(
        button for button in panel.findChildren(QPushButton) if button.text() == "Update Outdated"
    )
    assert update_button.isHidden()

    change: PromptChange = PromptChange(added_class_names=("bird",), removed_class_names=(), edited_class_names=())
    panel.set_prompt_changes({Path("c.jpg"): change, Path("a.jpg"): change})
    assert panel.outdated_image_paths == (Path("a.jpg"), Path("c.jpg"))
    assert not update_button.isHidden()
    summary_label: QLabel = next(label for label in panel.findChildren(QLabel) if "detections" in label.text())
    assert "2 outdated" in summary_label.text()

    table_view: QTableView | None = panel.findChild(QTableView)
    assert table_view is not None
    rows: dict[str, int] = {
        table_view.model().index(row, ResultColumn.IMAGE.value).data(): row
        for row in range(table_view.model().rowCount())
    }
    outdated_index = table_view.model().index(rows["c.jpg"], ResultColumn.IMAGE.value)
    current_index = table_view.model().index(rows["b.jpg"], ResultColumn.IMAGE.value)
    assert outdated_index.data(Qt.ItemDataRole.DecorationRole) is not None
    assert "added bird" in outdated_index.data(Qt.ItemDataRole.ToolTipRole)
    assert current_index.data(Qt.ItemDataRole.DecorationRole) is None

    update_button.click()
    assert update_requests == [True]
    panel.set_prompt_changes({})
    assert not panel.outdated_image_paths
    assert update_button.isHidden()


def _catalog_panel() -> tuple[ResultPanel, DetectionCatalog]:
    result_panel: ResultPanel = ResultPanel(ClassPalette())
    result_panel.add_images([Path("a.jpg"), Path("b.jpg")])
    catalog: DetectionCatalog = DetectionCatalog()
    for image_name, class_ids, confidences in (("a.jpg", [0, 1], [0.3, 0.9]), ("b.jpg", [1], [0.6])):
        catalog.record(
            Path(image_name),
            DetectionResult.from_xyxy(
                xyxy=np.tile(np.array([0.0, 0.0, 10.0, 10.0]), (len(class_ids), 1)),
                confidences=np.array(confidences, dtype=np.float64),
                query_ids=np.array(class_ids, dtype=np.int64),
                prompt=Prompt.from_class_names(("cat", "dog")),
                image_size=ImageSize(width=100, height=50),
            ),
            CAT_DOG_PROMPT,
        )
    result_panel.show_catalog(catalog)
    return result_panel, catalog


def test_unchecking_keep_rejects_the_detection_in_the_catalog(application: QApplication) -> None:
    result_panel, catalog = _catalog_panel()
    changed_images: list[Path] = []
    result_panel.acceptance_changed.connect(changed_images.append)
    table_view: QTableView = _table_view(result_panel)
    keep_index = table_view.model().index(0, ResultColumn.ACCEPTED.value)
    assert keep_index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked
    assert table_view.model().setData(keep_index, Qt.CheckState.Unchecked.value, Qt.ItemDataRole.CheckStateRole)
    assert catalog.rejected_indices_of(Path("a.jpg")) == frozenset({0})
    assert keep_index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Unchecked
    assert changed_images == [Path("a.jpg")]
    summary: QLabel | None = result_panel.findChild(QLabel)
    assert summary is not None and "1 rejected" in summary.text()


def test_space_toggles_the_selected_detection_and_the_menu_rejects_every_listed_one(
    application: QApplication,
) -> None:
    result_panel, catalog = _catalog_panel()
    table_view: QTableView = _table_view(result_panel)
    table_view.selectRow(1)
    record: DetectionRecord | None = result_panel.selected_record
    assert record is not None
    result_panel._toggle_selected()
    assert not result_panel.is_accepted(record)
    result_panel._toggle_selected()
    assert result_panel.is_accepted(record)

    result_panel.set_column_filter(ResultColumn.CONFIDENCE, RangeCondition(None, 0.7))
    result_panel.set_listed_accepted(False)
    assert catalog.rejected_indices_of(Path("a.jpg")) == frozenset({0})
    assert catalog.rejected_indices_of(Path("b.jpg")) == frozenset({0})

    result_panel.clear_filters()
    result_panel.set_column_filter(ResultColumn.ACCEPTED, ValueCondition(frozenset({"Rejected"})))
    assert _listed(result_panel) == [("a.jpg", "cat", 0.3), ("b.jpg", "dog", 0.6)]


def test_listed_detections_are_saved_as_csv_in_display_order(application: QApplication, tmp_path: Path) -> None:
    result_panel, _ = _catalog_panel()
    result_panel.set_accepted((result_panel.visible_records[0],), False)
    result_panel.set_column_filter(ResultColumn.CONFIDENCE, RangeCondition(0.5, None))
    _table_view(result_panel).sortByColumn(ResultColumn.CONFIDENCE.value, Qt.SortOrder.AscendingOrder)
    table_path: Path = tmp_path / "table.csv"
    assert result_panel.save_listed_table(table_path) == 2
    with table_path.open(encoding="utf-8", newline="") as table_file:
        rows: list[list[str]] = list(csv.reader(table_file))
    assert rows[0] == ["image", "class", "prompt", "confidence", "x1", "y1", "x2", "y2", "kept"]
    assert [(row[0], row[1], float(row[3]), row[8]) for row in rows[1:]] == [
        ("b.jpg", "dog", 0.6, "true"),
        ("a.jpg", "dog", 0.9, "true"),
    ]

    result_panel.clear_filters()
    assert result_panel.save_listed_table(table_path) == 3
    with table_path.open(encoding="utf-8", newline="") as table_file:
        assert [row[8] for row in csv.reader(table_file)][1:] == ["false", "true", "true"]


def test_saving_the_table_needs_listed_results(panel: ResultPanel, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        panel.save_listed_table(tmp_path / "table.csv")


def test_class_minimums_hide_detections_below_them(application: QApplication) -> None:
    result_panel, _ = _catalog_panel()
    listing_changes: list[None] = []
    result_panel.listing_changed.connect(lambda: listing_changes.append(None))
    result_panel.set_class_thresholds(ClassThresholds(0.0, {"dog": 0.7}))
    assert _listed(result_panel) == [("a.jpg", "cat", 0.3), ("a.jpg", "dog", 0.9)]
    assert result_panel.listed_detection_indices(Path("a.jpg")) == frozenset({0, 1})
    assert result_panel.listed_detection_indices_by_image() == {Path("a.jpg"): frozenset({0, 1})}
    assert listing_changes
    summary: QLabel | None = result_panel.findChild(QLabel)
    assert summary is not None and "1 below class minimums" in summary.text()


def test_removed_images_are_no_longer_listed(application: QApplication) -> None:
    result_panel, _ = _catalog_panel()
    result_panel.set_current_image(Path("a.jpg"))
    result_panel.remove_images([Path("a.jpg"), Path("missing.jpg")])
    assert _listed(result_panel) == [("b.jpg", "dog", 0.6)]
    assert not any(result_panel.is_current(row) for row in result_panel.visible_rows)


def test_columns_fit_their_contents_until_the_user_resizes_one(application: QApplication) -> None:
    result_panel, _ = _catalog_panel()
    header = _table_view(result_panel).horizontalHeader()
    assert header.sectionResizeMode(ResultColumn.IMAGE.value) == QHeaderView.ResizeMode.Interactive
    header.resizeSection(ResultColumn.IMAGE.value, 333)
    result_panel.add_images([Path("a_much_longer_image_name_than_before.jpg")])
    assert header.sectionSize(ResultColumn.IMAGE.value) == 333
