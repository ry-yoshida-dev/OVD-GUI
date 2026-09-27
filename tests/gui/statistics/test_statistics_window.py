from pathlib import Path

import numpy as np
from open_vocabulary_detector import (
    DetectionResult,
    DetectionThresholds,
    DetectorBackend,
    Device,
    ImageSize,
    PromptKind,
)
from PySide6.QtWidgets import QApplication, QComboBox, QDoubleSpinBox, QTableWidget

from ovd_gui.analysis import ProfileComparison, ResultStatistics
from ovd_gui.detection import DetectionCatalog, DetectorProfile, LabeledPrompt, ReferenceBoard
from ovd_gui.gui.class_palette import ClassPalette
from ovd_gui.gui.statistics import MinimumSpinBox, StatisticsColumn, StatisticsWindow
from ovd_gui.review import ClassThresholds
from ovd_gui.vocabulary import ClassDefinition

LABELED_PROMPT: LabeledPrompt = ReferenceBoard().build_prompt(
    (ClassDefinition.named("cat"), ClassDefinition.named("dog")), frozenset({PromptKind.TEXT})
)
PROFILE: DetectorProfile = DetectorProfile(
    backend=DetectorBackend.YOLO_WORLD,
    weights_path="yolov8s-worldv2.pt",
    device=Device.CPU,
    is_half_precision_enabled=False,
    thresholds=DetectionThresholds(confidence_threshold=0.1, nms_iou_threshold=0.7),
)


def _catalog() -> DetectionCatalog:
    catalog: DetectionCatalog = DetectionCatalog()
    catalog.record(
        Path("a.jpg"),
        DetectionResult.from_xyxy(
            xyxy=np.array([[0, 0, 10, 10], [20, 20, 30, 30], [40, 40, 50, 50]], dtype=np.float64),
            confidences=np.array([0.2, 0.6, 0.8]),
            query_ids=np.array([0, 0, 1], dtype=np.int64),
            prompt=LABELED_PROMPT.prompt,
            image_size=ImageSize(width=100, height=100),
        ),
        LABELED_PROMPT,
    )
    return catalog


def _window(thresholds: ClassThresholds) -> StatisticsWindow:
    window: StatisticsWindow = StatisticsWindow(ClassPalette())
    window.show_statistics(
        ResultStatistics.of(_catalog(), (Path("a.jpg"),), ("cat", "dog"), thresholds),
        "yolo",
        ("cat", "dog"),
        thresholds,
    )
    return window


def _class_table(window: StatisticsWindow) -> QTableWidget:
    tables: list[QTableWidget] = window.findChildren(QTableWidget)
    return tables[0]


def test_class_rows_count_detections_and_the_histogram_follows_the_selection(application: QApplication) -> None:
    window: StatisticsWindow = _window(ClassThresholds(0.0, {"cat": 0.5}))
    table: QTableWidget = _class_table(window)
    assert table.rowCount() == 2
    kept_item = table.item(0, StatisticsColumn.KEPT.value)
    assert kept_item is not None and kept_item.text() == "1"
    below_item = table.item(0, StatisticsColumn.BELOW_MINIMUM.value)
    assert below_item is not None and below_item.text() == "1"
    assert window.histogram.total_count == 3
    table.selectRow(1)
    assert window.selected_class_name == "dog"
    assert window.histogram.total_count == 1


def test_editing_minimums_reports_new_thresholds(application: QApplication) -> None:
    window: StatisticsWindow = _window(ClassThresholds())
    reported: list[ClassThresholds] = []
    window.thresholds_changed.connect(reported.append)
    spin = _class_table(window).cellWidget(1, StatisticsColumn.MINIMUM.value)
    assert isinstance(spin, MinimumSpinBox)
    assert spin.minimum_confidence is None
    spin.setValue(0.45)
    assert reported[-1] == ClassThresholds(0.0, {"dog": 0.45})
    spin.setValue(spin.minimum())
    assert reported[-1] == ClassThresholds()
    default_spin: QDoubleSpinBox | None = next(
        (child for child in window.findChildren(QDoubleSpinBox) if not isinstance(child, MinimumSpinBox)), None
    )
    assert default_spin is not None
    default_spin.setValue(0.3)
    assert reported[-1] == ClassThresholds(0.3)


def test_choosing_a_model_to_compare_reports_it(application: QApplication) -> None:
    window: StatisticsWindow = _window(ClassThresholds())
    selected: list[DetectorProfile] = []
    cleared: list[None] = []
    window.comparison_selected.connect(selected.append)
    window.comparison_cleared.connect(lambda: cleared.append(None))
    window.set_comparison_candidates((PROFILE,), None)
    combo: QComboBox | None = window.findChild(QComboBox)
    assert combo is not None and combo.count() == 2
    combo.setCurrentIndex(1)
    assert selected == [PROFILE]
    assert window.compared_profile == PROFILE
    window.show_comparison(ProfileComparison.between(_catalog(), _catalog(), (Path("a.jpg"),), ("cat", "dog")))
    comparison_table: QTableWidget = window.findChildren(QTableWidget)[1]
    matched_item = comparison_table.item(0, 3)
    assert matched_item is not None and matched_item.text() == "2"
    combo.setCurrentIndex(0)
    assert cleared == [None]
