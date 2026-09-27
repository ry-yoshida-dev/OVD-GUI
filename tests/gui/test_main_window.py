import time
from collections.abc import Iterator, Sequence
from dataclasses import replace
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest
from object_detection_format import AnnotationFormat
from open_vocabulary_detector import (
    DetectionResult,
    DetectorBackend,
    ImageSize,
    OpenVocabularyDetector,
    Prompt,
    PromptKind,
)
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QTableView

from ovd_gui.detection import DetectionOutcome, DetectorProfile, DeviceAvailability, ReferenceBox, ReferenceImage
from ovd_gui.export import ExportOptions, ExportScope
from ovd_gui.gui import MainWindow
from ovd_gui.gui.execution import BatchJob
from ovd_gui.gui.sidebar import ImageState, ImageStatus
from ovd_gui.gui.table import AnalysisState, ImageStatusRow, ProfilePanel, ResultColumn, ResultPanel, ValueCondition
from ovd_gui.preset import PresetCatalog
from ovd_gui.review import ClassThresholds
from ovd_gui.storage import ClassSetStore, ClassThresholdStore, ResultStore, SessionStore
from ovd_gui.vocabulary import ClassDefinition, ClassListStore

_REFERENCE_IMAGE: ReferenceImage = ReferenceImage.of("a.jpg", Image.new("RGB", (10, 10)))


class WidthCountingDetector(OpenVocabularyDetector):
    BACKEND: ClassVar[DetectorBackend] = DetectorBackend.GROUNDING_DINO
    failing_widths: frozenset[int] = frozenset()

    def _detect_mini_batch(self, images: Sequence[Image.Image], prompt: Prompt) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        for image in images:
            if image.width in self.failing_widths:
                raise ValueError("unsupported image")
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
    main_window: MainWindow = MainWindow(
        PresetCatalog.from_package(),
        ClassListStore(tmp_path / "data"),
        ClassSetStore(tmp_path / "data"),
        DeviceAvailability(is_cuda_available=False, is_mps_available=False),
        ResultStore(tmp_path / "data"),
        ClassThresholdStore(tmp_path / "data"),
        SessionStore(tmp_path / "data"),
    )
    main_window._class_editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.named("dog")))
    main_window._runner._worker._session._detector = WidthCountingDetector(
        main_window._settings_panel.current_settings()
    )
    main_window.open_paths([image_directory])
    yield main_window
    main_window.close()


def _wait_until_idle(application: QApplication, window: MainWindow) -> None:
    deadline: float = time.monotonic() + 10.0
    while not window._runner.is_idle and time.monotonic() < deadline:
        application.processEvents()
    assert window._runner.is_idle


def _result_table(window: MainWindow) -> QTableView:
    table_view: QTableView | None = _child(window, ResultPanel).findChild(QTableView)
    assert table_view is not None
    return table_view


def _child[WidgetType: ResultPanel | ProfilePanel | QTableView](
    window: MainWindow, widget_type: type[WidgetType]
) -> WidgetType:
    widget: WidgetType | None = window.findChild(widget_type)
    assert widget is not None
    return widget


def test_opened_images_are_listed_as_not_analyzed(window: MainWindow) -> None:
    panel: ResultPanel = _child(window, ResultPanel)
    assert [(row.image_path.name, row.state) for row in panel.visible_rows if isinstance(row, ImageStatusRow)] == [
        (f"image{index}.png", AnalysisState.NOT_ANALYZED) for index in range(3)
    ]
    assert [row.image_path.name for row in panel.visible_rows if panel.is_current(row)] == ["image0.png"]
    table_view: QTableView = _result_table(window)
    table_view.selectRow(2)
    assert window._current_image is not None
    assert window._current_image.path.name == "image2.png"


def test_detect_all_lists_every_image_and_opens_the_image_of_a_selected_row(
    application: QApplication, window: MainWindow
) -> None:
    window._detect_all()
    _wait_until_idle(application, window)
    panel: ResultPanel = _child(window, ResultPanel)
    assert len(panel.visible_records) == 6

    panel.set_column_filter(ResultColumn.CLASS, ValueCondition(frozenset({"dog"})))
    assert [(record.image_path.name, record.detection_index) for record in panel.visible_records] == [
        ("image1.png", 1),
        ("image2.png", 1),
    ]

    table_view: QTableView = _result_table(window)
    table_view.sortByColumn(ResultColumn.CONFIDENCE.value, Qt.SortOrder.AscendingOrder)
    table_view.selectRow(0)
    assert window._current_image is not None
    assert window._current_image.path.name == "image2.png"
    assert window._image_list.currentRow() == 2


def test_stored_results_are_shown_again_and_can_be_cleared(application: QApplication, window: MainWindow) -> None:
    window._detect_all()
    _wait_until_idle(application, window)
    window._image_list.setCurrentRow(1)
    assert list(window._canvas.drawn_indices) == [0, 1]
    window._clear_results()
    assert _child(window, ResultPanel).visible_records == ()
    assert len(_child(window, ResultPanel).visible_rows) == 3
    window._image_list.setCurrentRow(2)
    assert list(window._canvas.drawn_indices) == []


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


def test_reference_only_classes_are_skipped_after_confirmation(
    application: QApplication, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert PromptKind.VISUAL not in window._settings_panel.selected_backend.supported_prompt_kinds
    window._class_editor.set_classes((ClassDefinition.parse("mug:"), ClassDefinition.named("dog")))
    window._reference_board.add(ReferenceBox(_REFERENCE_IMAGE, "mug", 0.0, 0.0, 5.0, 5.0), Image.new("RGB", (10, 10)))
    questions: list[str] = []
    answers: list[QMessageBox.StandardButton] = [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes]

    def answer_question(*arguments: object) -> QMessageBox.StandardButton:
        questions.append(str(arguments[2]))
        return answers.pop(0)

    monkeypatch.setattr(QMessageBox, "question", answer_question)
    window._detect_all()
    assert not window._runner.is_busy
    window._detect_all()
    _wait_until_idle(application, window)
    assert {record.detection.class_name for record in _child(window, ResultPanel).visible_records} == {"dog"}
    window._detect_all()
    _wait_until_idle(application, window)
    assert len(questions) == 2
    assert "mug" in questions[0]


def test_detect_all_runs_in_the_background_with_cancellable_progress_in_the_status_bar(
    application: QApplication, window: MainWindow
) -> None:
    window._detect_all()
    assert window._batch_progress_dialog.isHidden()
    assert not window._run_progress_indicator.isHidden()
    assert window._run_progress_indicator._progress_bar.maximum() == 3
    assert not window._run_progress_indicator._cancel_button.isHidden()
    assert window._class_editor.isEnabled()

    window._run_progress_indicator._cancel_button.click()
    assert not window._run_progress_indicator._cancel_button.isEnabled()
    _wait_until_idle(application, window)
    assert window._run_progress_indicator.isHidden()
    assert window._batch_progress_dialog.isHidden()


def _detected_image_names(window: MainWindow) -> set[str]:
    return {record.image_path.name for record in _child(window, ResultPanel).visible_records}


def _record_background_order(window: MainWindow) -> list[str]:
    detected_order: list[str] = []

    def record_order(outcome: DetectionOutcome) -> None:
        detected_order.append(outcome.request.image_path.name)

    window._runner.background_succeeded.connect(record_order)
    return detected_order


def test_every_open_image_is_detected_in_the_background_without_blocking_the_window(
    application: QApplication, window: MainWindow
) -> None:
    detected_order: list[str] = _record_background_order(window)
    assert not window._runner.is_idle
    assert not window._runner.is_busy
    assert window._detect_button.isEnabled()
    assert window._settings_panel.isEnabled()
    _wait_until_idle(application, window)
    assert detected_order == ["image0.png", "image1.png", "image2.png"]
    assert len(window._canvas.drawn_indices) == 1


def test_newly_shown_image_is_detected_before_the_other_images(application: QApplication, window: MainWindow) -> None:
    detected_order: list[str] = _record_background_order(window)
    window._image_list.setCurrentRow(1)
    window._image_list.setCurrentRow(2)
    _wait_until_idle(application, window)
    assert detected_order == ["image0.png", "image2.png", "image1.png"]
    assert len(window._canvas.drawn_indices) == 3


def test_unreadable_images_are_skipped_by_background_detection(application: QApplication, window: MainWindow) -> None:
    detected_order: list[str] = _record_background_order(window)
    window._image_list.image_paths[1].write_bytes(b"not an image")
    _wait_until_idle(application, window)
    assert detected_order == ["image0.png", "image2.png"]


def test_failed_background_detection_pauses_the_other_images_and_is_not_retried(
    application: QApplication, window: MainWindow
) -> None:
    detected_order: list[str] = _record_background_order(window)
    detector: OpenVocabularyDetector | None = window._runner._worker._session._detector
    assert isinstance(detector, WidthCountingDetector)
    detector.failing_widths = frozenset({64})
    _wait_until_idle(application, window)
    assert detected_order == ["image0.png"]
    assert "image1.png failed" in window.statusBar().currentMessage()

    window._image_list.setCurrentRow(2)
    _wait_until_idle(application, window)
    assert detected_order == ["image0.png", "image2.png"]


def test_detect_all_starts_after_the_background_detection_and_detects_the_shown_image_first(
    application: QApplication, window: MainWindow
) -> None:
    detected_order: list[str] = []

    def record_order(job: BatchJob, image_path: Path, result: DetectionResult) -> None:
        detected_order.append(image_path.name)

    window._runner.batch_image_detected.connect(record_order)
    window._detect_all()
    assert window._runner.is_busy
    assert not window._detect_button.isEnabled()
    window._image_list.setCurrentRow(2)
    assert window.statusBar().currentMessage() != "A detection is already running."
    _wait_until_idle(application, window)
    assert detected_order == ["image2.png", "image0.png", "image1.png"]
    assert len(_child(window, ResultPanel).visible_records) == 6


def test_results_of_each_model_are_kept_and_shown_again_without_detecting(
    application: QApplication, window: MainWindow
) -> None:
    window._detect_all()
    _wait_until_idle(application, window)
    window._settings_panel._confidence_spin.setValue(0.9)
    window._image_list.setCurrentRow(2)
    window._request_detection()
    _wait_until_idle(application, window)
    panel: ResultPanel = _child(window, ResultPanel)
    assert len(panel.visible_records) == 6
    assert [row for row in panel.visible_rows if isinstance(row, ImageStatusRow)] == []

    profile_panel: ProfilePanel = _child(window, ProfilePanel)
    first_profile, second_profile = profile_panel.profiles
    assert profile_panel.selected_profile == second_profile
    profile_panel.select_profile(first_profile)
    assert not window._runner.is_busy
    assert len(panel.visible_records) == 6
    assert len(window._canvas.drawn_indices) == 3

    window._remove_profile(first_profile)
    assert profile_panel.profiles == (second_profile,)
    assert profile_panel.selected_profile == second_profile
    assert len(panel.visible_records) == 6


def test_editing_classes_keeps_results_but_marks_them_outdated_until_updated(
    application: QApplication, window: MainWindow
) -> None:
    window._detect_all()
    _wait_until_idle(application, window)
    panel: ResultPanel = _child(window, ResultPanel)
    profile_panel: ProfilePanel = _child(window, ProfilePanel)
    assert panel.outdated_image_paths == ()

    window._class_editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.parse("dog: dog, puppy")))
    assert len(panel.visible_records) == 6
    assert panel.outdated_image_paths == window._image_list.image_paths
    assert window._result_library.summaries(window._current_signature())[0].outdated_image_count == 3
    assert profile_panel.profiles == window._result_library.profiles

    window._update_outdated()
    assert window._runner.is_busy
    _wait_until_idle(application, window)
    assert panel.outdated_image_paths == ()
    assert window._result_library.summaries(window._current_signature())[0].outdated_image_count == 0


def _settle(application: QApplication, milliseconds: int = 150) -> None:
    deadline: float = time.monotonic() + milliseconds / 1000.0
    while time.monotonic() < deadline:
        application.processEvents()


def _detected_window(application: QApplication, window: MainWindow) -> MainWindow:
    window._detect_all()
    _wait_until_idle(application, window)
    window._image_list.setCurrentRow(2)
    _wait_until_idle(application, window)
    return window


def test_the_image_draws_only_listed_detections_and_marks_rejected_ones(
    application: QApplication, window: MainWindow
) -> None:
    _detected_window(application, window)
    panel: ResultPanel = _child(window, ResultPanel)
    assert list(window._canvas.drawn_indices) == [0, 1, 2]

    panel.set_column_filter(ResultColumn.CLASS, ValueCondition(frozenset({"cat"})))
    assert list(window._canvas.drawn_indices) == [0, 2]
    panel.clear_filters()

    image_path: Path = window._image_list.image_paths[2]
    first_record = next(record for record in panel.visible_records if record.image_path == image_path)
    panel.set_accepted((first_record,), False)
    assert list(window._canvas.drawn_indices) == [0, 1, 2]
    window._canvas.set_display_options(replace(window._canvas.display_options, is_rejected_shown=False))
    assert list(window._canvas.drawn_indices) == [1, 2]
    _settle(application)
    assert window._image_list.status_of(image_path) == ImageStatus(ImageState.DETECTED, 2, 3)


def test_class_minimums_hide_detections_and_are_remembered(
    application: QApplication, window: MainWindow, tmp_path: Path
) -> None:
    _detected_window(application, window)
    window._apply_class_thresholds(ClassThresholds(0.0, {"cat": 0.5}))
    assert list(window._canvas.drawn_indices) == [1, 2]
    assert ClassThresholdStore(tmp_path / "data").load() == ClassThresholds(0.0, {"cat": 0.5})


def test_closing_images_keeps_their_results_and_shows_the_drop_zone_when_none_is_left(
    application: QApplication, window: MainWindow
) -> None:
    _detected_window(application, window)
    closed_path: Path = window._image_list.image_paths[2]
    window.close_images((closed_path,))
    assert closed_path not in window._image_list.image_paths
    assert closed_path not in {record.image_path for record in _child(window, ResultPanel).visible_records}
    assert window._current_image is not None and window._current_image.path != closed_path

    window.close_images(window._image_list.image_paths)
    assert window._current_image is None
    assert window._center_stack.currentWidget() is window._drop_zone
    assert window._result_library.catalog_of(window._result_library.profiles[0]).result_of(closed_path) is not None


def test_previous_and_next_image_follow_the_list(application: QApplication, window: MainWindow) -> None:
    assert not window._previous_image_action.isEnabled()
    window._show_neighbor_image(1)
    assert window._image_list.currentRow() == 1
    window._show_neighbor_image(1)
    assert not window._next_image_action.isEnabled()
    window._show_neighbor_image(-1)
    assert window._image_list.currentRow() == 1


def _read_yolo_labels(directory: Path) -> dict[str, int]:
    return {
        path.stem: len([line for line in path.read_text().splitlines() if line.strip()])
        for path in directory.glob("image*.txt")
    }


def test_export_writes_stored_kept_detections_without_detecting_again(
    application: QApplication, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _detected_window(application, window)
    panel: ResultPanel = _child(window, ResultPanel)
    rejected = next(record for record in panel.visible_records if record.image_path.name == "image1.png")
    panel.set_accepted((rejected,), False)
    output_directory: Path = tmp_path / "labels"
    asked: list[tuple[str, int, int]] = []

    def ask(model_name: str, image_count: int, pending_count: int) -> ExportOptions:
        asked.append((model_name, image_count, pending_count))
        return ExportOptions(AnnotationFormat.YOLO, output_directory, is_confidence_included=False)

    monkeypatch.setattr(window._export_dialog, "ask", ask)
    window._export_detections()
    assert not window._runner.is_busy
    assert asked[0][1:] == (3, 0)
    assert _read_yolo_labels(output_directory) == {"image0": 1, "image1": 1, "image2": 3}

    panel.set_column_filter(ResultColumn.CLASS, ValueCondition(frozenset({"dog"})))
    listed_directory: Path = tmp_path / "listed"
    monkeypatch.setattr(
        window._export_dialog,
        "ask",
        lambda *arguments: ExportOptions(
            AnnotationFormat.YOLO, listed_directory, is_confidence_included=False, scope=ExportScope.LISTED
        ),
    )
    window._export_detections()
    assert _read_yolo_labels(listed_directory) == {"image0": 0, "image1": 1, "image2": 1}


def test_export_detects_images_without_an_up_to_date_result_first(
    application: QApplication, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _wait_until_idle(application, window)
    window._class_editor.set_classes((ClassDefinition.named("cat"),))
    output_directory: Path = tmp_path / "labels"
    asked: list[int] = []

    def ask(model_name: str, image_count: int, pending_count: int) -> ExportOptions:
        asked.append(pending_count)
        return ExportOptions(AnnotationFormat.YOLO, output_directory, is_confidence_included=False)

    monkeypatch.setattr(window._export_dialog, "ask", ask)
    window._background_queue.pin()
    window._export_detections()
    _wait_until_idle(application, window)
    assert asked and asked[0] > 0
    assert _read_yolo_labels(output_directory) == {"image0": 1, "image1": 2, "image2": 3}


def test_results_and_rejections_are_restored_at_the_next_start(
    application: QApplication, window: MainWindow, tmp_path: Path
) -> None:
    _detected_window(application, window)
    panel: ResultPanel = _child(window, ResultPanel)
    panel.set_accepted((panel.visible_records[0],), False)
    window.save_results()

    restored: MainWindow = MainWindow(
        PresetCatalog.from_package(),
        ClassListStore(tmp_path / "data"),
        ClassSetStore(tmp_path / "data"),
        DeviceAvailability(is_cuda_available=False, is_mps_available=False),
        ResultStore(tmp_path / "data"),
        ClassThresholdStore(tmp_path / "data"),
        SessionStore(tmp_path / "data"),
    )
    restored._class_editor.set_classes((ClassDefinition.named("cat"), ClassDefinition.named("dog")))
    restored.open_paths([tmp_path / "images"])
    assert restored._runner.is_idle
    restored_panel: ResultPanel = _child(restored, ResultPanel)
    assert len(restored_panel.visible_records) == 6
    assert not restored_panel.is_accepted(restored_panel.visible_records[0])
    restored.close()


def test_export_also_saves_images_with_boxes_drawn(
    application: QApplication, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _detected_window(application, window)
    output_directory: Path = tmp_path / "labels"
    monkeypatch.setattr(
        window._export_dialog,
        "ask",
        lambda *arguments: ExportOptions(
            AnnotationFormat.YOLO, output_directory, is_confidence_included=False, is_annotated_image_saved=True
        ),
    )
    window._export_detections()
    annotated_directory: Path = output_directory / ExportOptions.ANNOTATED_IMAGE_DIRECTORY_NAME
    assert sorted(path.name for path in annotated_directory.iterdir()) == [f"image{index}.png" for index in range(3)]
    with Image.open(annotated_directory / "image2.png") as annotated:
        assert annotated.size == (96, 16)
        assert annotated.getpixel((1, 5)) != (0, 0, 0)


def _new_window(tmp_path: Path) -> MainWindow:
    return MainWindow(
        PresetCatalog.from_package(),
        ClassListStore(tmp_path / "data"),
        ClassSetStore(tmp_path / "data"),
        DeviceAvailability(is_cuda_available=False, is_mps_available=False),
        ResultStore(tmp_path / "data"),
        ClassThresholdStore(tmp_path / "data"),
        SessionStore(tmp_path / "data"),
    )


def test_open_images_and_the_shown_one_are_restored_at_the_next_start(
    application: QApplication, window: MainWindow, tmp_path: Path
) -> None:
    image_paths: tuple[Path, ...] = window._image_list.image_paths
    window.close_images((image_paths[0],))
    window._image_list.select(image_paths[2])
    window.close()

    restored: MainWindow = _new_window(tmp_path)
    restored.restore_session()
    assert restored._image_list.image_paths == image_paths[1:]
    assert restored._image_list.current_path == image_paths[2]
    restored.close()

    image_paths[1].unlink()
    reopened: MainWindow = _new_window(tmp_path)
    reopened.restore_session()
    assert reopened._image_list.image_paths == (image_paths[2],)
    assert "1 missing skipped" in reopened.statusBar().currentMessage()
    reopened.close()


def test_another_model_is_compared_in_statistics_and_drawn_over_the_image(
    application: QApplication, window: MainWindow
) -> None:
    _detected_window(application, window)
    first_profile: DetectorProfile = window._result_library.profiles[0]
    window._settings_panel._confidence_spin.setValue(0.9)
    window._request_detection()
    _wait_until_idle(application, window)
    assert window._shown_profile != first_profile

    window._show_statistics_window()
    window._statistics_window.set_comparison_candidates((first_profile,), None)
    window._compare_with(first_profile)
    assert window._canvas.drawn_comparison_count == 3
    assert window._statistics_window.compared_profile == first_profile
    window._compare_with(None)
    assert window._canvas.drawn_comparison_count == 0
    window._statistics_window.close()
