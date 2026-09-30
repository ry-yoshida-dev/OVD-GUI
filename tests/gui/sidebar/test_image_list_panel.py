from pathlib import Path

import numpy as np
from open_vocabulary_detector import DetectionResult, ImageSize, Prompt, PromptKind
from PySide6.QtWidgets import QApplication

from ovd_gui.detection import DetectionCatalog, LabeledPrompt, ReferenceBoard
from ovd_gui.gui.sidebar import ImageCountDelegate, ImageListPanel
from ovd_gui.review import ClassThresholds
from ovd_gui.vocabulary import ClassDefinition
from ovd_gui.workspace import ImageState, ImageStatus

PATHS: tuple[Path, ...] = tuple(Path(f"image{index}.png") for index in range(4))


def _panel() -> ImageListPanel:
    panel: ImageListPanel = ImageListPanel()
    panel.add_images(PATHS)
    return panel


def test_closing_the_current_image_makes_the_next_one_current(application: QApplication) -> None:
    panel: ImageListPanel = _panel()
    changes: list[None] = []
    panel.current_image_changed.connect(lambda: changes.append(None))
    panel.select(PATHS[1])
    changes.clear()
    panel.remove_images((PATHS[1], PATHS[3], Path("missing.png")))
    assert panel.image_paths == (PATHS[0], PATHS[2])
    assert panel.current_path == PATHS[2]
    assert len(changes) == 1
    assert panel.title == "Images (2)"


def test_closing_another_image_keeps_the_current_one(application: QApplication) -> None:
    panel: ImageListPanel = _panel()
    panel.select(PATHS[2])
    panel.remove_images((PATHS[0],))
    assert panel.current_path == PATHS[2]
    panel.remove_images(panel.image_paths)
    assert panel.current_path is None


def test_neighbors_are_selected_within_the_list(application: QApplication) -> None:
    panel: ImageListPanel = _panel()
    assert not panel.select_neighbor(-1)
    assert panel.select_neighbor(1)
    assert panel.current_path == PATHS[1]
    panel.select(PATHS[3])
    assert not panel.select_neighbor(1)
    assert panel.current_path == PATHS[3]


def test_selected_images_are_requested_for_closing(application: QApplication) -> None:
    panel: ImageListPanel = _panel()
    requested: list[tuple[Path, ...]] = []
    panel.removal_requested.connect(requested.append)
    panel.item(0).setSelected(True)
    panel.item(2).setSelected(True)
    panel._request_removal_of_selection()
    assert requested == [(PATHS[0], PATHS[2])]


def test_statuses_mark_rows_with_their_state_and_kept_count(application: QApplication) -> None:
    panel: ImageListPanel = _panel()
    panel.set_statuses({PATHS[0]: ImageStatus(ImageState.DETECTED, 2, 3), PATHS[1]: ImageStatus(ImageState.FAILED)})
    assert panel.item(0).data(ImageCountDelegate.COUNT_ROLE) == "2/3"
    assert "2 of 3 detections kept" in panel.item(0).toolTip()
    assert panel.item(1).data(ImageCountDelegate.COUNT_ROLE) == ""
    assert panel.status_of(PATHS[2]).state == ImageState.NOT_ANALYZED


def test_status_of_an_image_counts_detections_kept_after_review() -> None:
    labeled_prompt: LabeledPrompt = ReferenceBoard().build_prompt(
        (ClassDefinition.named("cat"),), frozenset({PromptKind.TEXT})
    )
    catalog: DetectionCatalog = DetectionCatalog()
    catalog.record(
        PATHS[0],
        DetectionResult.from_xyxy(
            xyxy=np.tile(np.array([0.0, 0.0, 10.0, 10.0]), (3, 1)),
            confidences=np.array([0.2, 0.5, 0.9]),
            query_ids=np.zeros(3, dtype=np.int64),
            prompt=Prompt.from_class_names(("cat",)),
            image_size=ImageSize(width=100, height=50),
        ),
        labeled_prompt,
    )
    catalog.set_accepted(PATHS[0], (2,), is_accepted=False)
    thresholds: ClassThresholds = ClassThresholds(0.3)
    assert ImageStatus.of(PATHS[0], catalog, thresholds, is_outdated=True, is_failed=False) == ImageStatus(
        ImageState.OUTDATED, kept_count=1, detection_count=3
    )
    assert ImageStatus.of(PATHS[1], catalog, thresholds, is_outdated=False, is_failed=True).state == ImageState.FAILED
    assert ImageStatus.of(PATHS[1], None, thresholds, is_outdated=False, is_failed=False).state == (
        ImageState.NOT_ANALYZED
    )
