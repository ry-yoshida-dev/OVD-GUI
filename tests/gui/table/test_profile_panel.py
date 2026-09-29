from dataclasses import replace

import pytest
from open_vocabulary_detector import DetectionThresholds, DetectorBackend, DetectorSettings, Device
from PySide6.QtWidgets import QApplication, QHeaderView, QPushButton, QTreeWidget, QTreeWidgetItem

from ovd_gui.detection import DetectorProfile, ProfileSummary
from ovd_gui.gui.table import ProfileColumn, ProfilePanel

SMALL: DetectorProfile = DetectorProfile.of(
    DetectorSettings(
        backend=DetectorBackend.YOLO_WORLD,
        weights_path="yolov8s-worldv2.pt",
        thresholds=DetectionThresholds(confidence_threshold=0.25, nms_iou_threshold=None),
        device=Device.CPU,
    )
)
LARGE: DetectorProfile = replace(SMALL, weights_path="yolov8l-worldv2.pt")


@pytest.fixture
def panel(application: QApplication) -> ProfilePanel:
    profile_panel: ProfilePanel = ProfilePanel()
    profile_panel.set_summaries(
        (
            ProfileSummary(profile=SMALL, image_count=3, outdated_image_count=0, detection_count=7),
            ProfileSummary(profile=LARGE, image_count=1, outdated_image_count=0, detection_count=2),
        ),
        SMALL,
    )
    return profile_panel


def _tree(panel: ProfilePanel) -> QTreeWidget:
    tree: QTreeWidget | None = panel.findChild(QTreeWidget)
    assert tree is not None
    return tree


def test_rows_show_backend_model_options_and_counts_with_the_shown_profile_selected(panel: ProfilePanel) -> None:
    tree: QTreeWidget = _tree(panel)
    first_row: QTreeWidgetItem | None = tree.topLevelItem(0)
    assert first_row is not None
    assert [first_row.text(column.value) for column in ProfileColumn] == [
        "yolo_world",
        "yolov8s-worldv2",
        "cpu",
        "fp32",
        "0.25",
        "off",
        "3",
        "",
        "7",
    ]
    assert panel.profiles == (SMALL, LARGE)
    assert panel.selected_profile == SMALL


def test_selecting_a_row_reports_its_profile_but_listing_does_not(panel: ProfilePanel) -> None:
    selected: list[DetectorProfile] = []
    panel.profile_selected.connect(selected.append)
    panel.set_summaries(
        (ProfileSummary(profile=LARGE, image_count=1, outdated_image_count=0, detection_count=2),), LARGE
    )
    assert selected == []
    panel.set_summaries(
        (
            ProfileSummary(profile=SMALL, image_count=3, outdated_image_count=0, detection_count=7),
            ProfileSummary(profile=LARGE, image_count=1, outdated_image_count=0, detection_count=2),
        ),
        LARGE,
    )
    panel.select_profile(SMALL)
    assert selected == [SMALL]


def test_remove_button_requests_removal_of_the_selected_profile(panel: ProfilePanel) -> None:
    removed: list[DetectorProfile] = []
    panel.removal_requested.connect(removed.append)
    remove_button: QPushButton | None = panel.findChild(QPushButton)
    assert remove_button is not None
    remove_button.click()
    assert removed == [SMALL]
    panel.set_summaries((), None)
    assert not remove_button.isEnabled()


def test_unlisted_profiles_are_rejected(panel: ProfilePanel) -> None:
    with pytest.raises(KeyError):
        panel.select_profile(replace(SMALL, device=Device.CUDA))
    with pytest.raises(KeyError):
        panel.set_summaries(
            (ProfileSummary(profile=SMALL, image_count=0, outdated_image_count=0, detection_count=0),), LARGE
        )


def test_model_table_columns_can_be_resized(application: QApplication) -> None:
    panel: ProfilePanel = ProfilePanel()
    tree: QTreeWidget | None = panel.findChild(QTreeWidget)
    assert tree is not None
    assert tree.header().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
