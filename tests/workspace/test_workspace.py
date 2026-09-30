from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest
from object_detection_format import AnnotationFormat
from open_vocabulary_detector import DetectorBackend
from PIL import Image

from ovd_gui.detection import DetectionCatalog, DetectorProfile, ReferenceBox, ReferenceImage
from ovd_gui.export import ExportOptions, ExportScope
from ovd_gui.review import ClassThresholds
from ovd_gui.storage import Session
from ovd_gui.vocabulary import ClassDefinition
from ovd_gui.workspace import (
    ActionReply,
    ActionStatus,
    ExportRequest,
    ImageState,
    Notice,
    NoticeLevel,
    Workspace,
    WorkspaceStores,
)


def _catalog(workspace: Workspace) -> DetectionCatalog:
    catalog: DetectionCatalog | None = workspace.shown_catalog()
    assert catalog is not None
    return catalog


def test_opened_images_are_detected_in_the_background_shown_image_first(
    workspace: Workspace, image_directory: Path, wait_until_idle: Callable[[], None]
) -> None:
    workspace.open_paths([image_directory])
    assert workspace.current_path == image_directory.resolve() / "image0.png"
    assert workspace.background_image_path == workspace.current_path
    assert not workspace.is_busy
    wait_until_idle()
    assert _catalog(workspace).image_paths == workspace.image_paths
    assert [status.state for status in workspace.image_statuses().values()] == [ImageState.DETECTED] * 3
    assert [status.detection_count for status in workspace.image_statuses().values()] == [1, 2, 3]


def test_opening_the_same_folder_again_adds_nothing(workspace: Workspace, image_directory: Path) -> None:
    workspace.open_paths([image_directory])
    workspace.open_paths([image_directory])
    assert len(workspace.image_paths) == 3
    assert workspace.status_message.startswith("No new images found")


def test_edited_classes_mark_results_outdated_until_detected_again(
    workspace: Workspace, image_directory: Path, wait_until_idle: Callable[[], None]
) -> None:
    workspace.open_paths([image_directory])
    wait_until_idle()
    workspace.edit_classes(lambda bench: bench.add_class(2, "bird"))
    assert set(workspace.outdated_changes()) == set(workspace.image_paths)
    assert workspace.outdated_changes()[workspace.image_paths[0]].description == "added bird"
    wait_until_idle()
    assert workspace.outdated_changes() == {}


def test_invalid_class_edit_changes_nothing(workspace: Workspace) -> None:
    with pytest.raises(ValueError, match="already exists"):
        workspace.edit_classes(lambda bench: bench.add_class(0, "cat"))
    assert workspace.workbench.class_names == ("cat", "dog")


def test_detect_all_reports_progress_and_refuses_a_second_run(
    workspace: Workspace, image_directory: Path, wait_until_idle: Callable[[], None]
) -> None:
    workspace.open_paths([image_directory])
    wait_until_idle()
    reply: ActionReply = workspace.detect_all(is_skipping_approved=False)
    assert reply.status == ActionStatus.DONE
    assert workspace.is_busy
    assert workspace.progress is not None
    assert workspace.progress.title == "Detect All"
    second: ActionReply = workspace.detect_all(is_skipping_approved=False)
    assert second.status == ActionStatus.REJECTED
    assert second.message == "A detection is already running."
    wait_until_idle()
    assert workspace.progress is None
    assert workspace.status_message == "Detected 3 images."


def test_detect_without_images_is_refused(workspace: Workspace) -> None:
    reply: ActionReply = workspace.detect_current(is_skipping_approved=False)
    assert reply == ActionReply.rejected("Open an image first.")


def test_reference_only_class_needs_approval_with_a_text_only_model(
    workspace: Workspace, image_directory: Path, wait_until_idle: Callable[[], None]
) -> None:
    workspace.open_paths([image_directory])
    wait_until_idle()
    pixels: Image.Image = Image.new("RGB", (10, 10))
    reference: ReferenceImage = ReferenceImage.of("example.png", pixels)
    workspace.edit_classes(lambda bench: bench.set_classes((*bench.classes, ClassDefinition("bird", ()))))
    workspace.edit_classes(
        lambda bench: bench.add_reference_boxes((ReferenceBox(reference, "bird", 0, 0, 5, 5),), pixels)
    )
    assert DetectorBackend.GROUNDING_DINO == workspace.selection.backend
    reply: ActionReply = workspace.detect_current(is_skipping_approved=False)
    assert reply.status == ActionStatus.NEEDS_APPROVAL
    assert reply.skipped_class_names == ("bird",)
    approved: ActionReply = workspace.detect_current(is_skipping_approved=True)
    assert approved.status == ActionStatus.DONE
    wait_until_idle()


def test_failed_detection_is_reported_as_an_error_notice(
    workspace: Workspace,
    image_directory: Path,
    wait_until_idle: Callable[[], None],
    fail_width: Callable[[int], None],
    notices: list[Notice],
) -> None:
    fail_width(32)
    workspace.open_paths([image_directory])
    wait_until_idle()
    assert workspace.image_statuses()[workspace.image_paths[0]].state == ImageState.FAILED
    workspace.detect_current(is_skipping_approved=False)
    wait_until_idle()
    assert [(notice.level, notice.title) for notice in notices] == [(NoticeLevel.ERROR, "Detection failed")]


def test_rejected_detections_and_class_minimums_reduce_the_kept_count(
    workspace: Workspace, image_directory: Path, wait_until_idle: Callable[[], None]
) -> None:
    workspace.open_paths([image_directory])
    wait_until_idle()
    last_image: Path = workspace.image_paths[2]
    workspace.set_accepted({last_image: [0]}, is_accepted=False)
    assert workspace.image_statuses()[last_image].count_text == "2/3"
    workspace.set_class_thresholds(ClassThresholds(0.7))
    assert workspace.image_statuses()[last_image].count_text == "1/3"


def test_closing_the_shown_image_shows_the_next_one(workspace: Workspace, image_directory: Path) -> None:
    workspace.open_paths([image_directory])
    first, second, third = workspace.image_paths
    workspace.select_image(second)
    workspace.close_images([second])
    assert workspace.current_path == third
    workspace.close_images([third])
    assert workspace.current_path == first
    workspace.close_images([first])
    assert workspace.current_path is None


def test_session_is_restored_with_the_shown_image(
    workspace: Workspace, image_directory: Path, stores: WorkspaceStores
) -> None:
    workspace.open_paths([image_directory])
    workspace.select_image(workspace.image_paths[1])
    session: Session = Session(workspace.image_paths, workspace.image_paths[1])
    assert stores.session_store.load() == session
    workspace.close_images(workspace.image_paths)
    stores.session_store.save(session)
    workspace.restore_session()
    assert len(workspace.image_paths) == 3
    assert workspace.current_path == workspace.image_paths[1]


def test_results_are_saved_after_the_delay(
    workspace: Workspace,
    image_directory: Path,
    stores: WorkspaceStores,
    wait_until_idle: Callable[[], None],
    run_delayed_calls: Callable[[], None],
) -> None:
    workspace.open_paths([image_directory])
    wait_until_idle()
    assert not stores.result_store.path.exists()
    run_delayed_calls()
    assert len(stores.result_store.load().profiles) == 1


def test_export_detects_pending_images_then_writes_the_files(
    workspace: Workspace, image_directory: Path, tmp_path: Path, wait_until_idle: Callable[[], None]
) -> None:
    workspace.open_paths([image_directory])
    workspace.edit_classes(lambda bench: bench.add_class(2, "bird"))
    output_directory: Path = tmp_path / "export"
    options: ExportOptions = ExportOptions(
        annotation_format=AnnotationFormat.YOLO,
        output_directory=output_directory,
        is_confidence_included=False,
        is_annotated_image_saved=True,
    )
    reply: ActionReply = workspace.export(ExportRequest(options, None, is_confidence_shown=True), False)
    assert reply.status == ActionStatus.DONE
    wait_until_idle()
    assert workspace.last_export is not None
    assert workspace.last_export.detection_count == 6
    assert workspace.last_export.annotated_image_count == 3
    assert (output_directory / "annotated_images").is_dir()
    assert workspace.status_message.startswith("Exported YOLO (TXT): 3 images, 6 detections")


def test_selecting_a_stored_profile_pins_it(
    workspace: Workspace,
    image_directory: Path,
    wait_until_idle: Callable[[], None],
) -> None:
    workspace.open_paths([image_directory])
    wait_until_idle()
    first_profile: DetectorProfile | None = workspace.shown_profile
    assert first_profile is not None
    workspace.select_model(replace(workspace.selection, confidence_threshold=0.5))
    workspace.detect_current(is_skipping_approved=False)
    wait_until_idle()
    assert len(workspace.result_library.profiles) == 2
    assert workspace.shown_profile != first_profile
    workspace.select_profile(first_profile)
    assert workspace.background_image_path is None
    assert workspace.shown_profile == first_profile


def test_session_whose_shown_image_was_deleted_opens_the_remaining_images(
    workspace: Workspace, image_directory: Path, stores: WorkspaceStores
) -> None:
    workspace.open_paths([image_directory])
    first, second, third = workspace.image_paths
    workspace.close_images(workspace.image_paths)
    stores.session_store.save(Session((first, second, third), second))
    second.unlink()
    workspace.restore_session()
    assert workspace.image_paths == (first, third)
    assert workspace.current_path == first


def test_exporting_listed_detections_is_refused_while_images_are_pending(
    workspace: Workspace, image_directory: Path, tmp_path: Path, wait_until_idle: Callable[[], None]
) -> None:
    workspace.open_paths([image_directory])
    wait_until_idle()
    workspace.edit_classes(lambda bench: bench.add_class(2, "bird"))
    options: ExportOptions = ExportOptions(
        annotation_format=AnnotationFormat.YOLO,
        output_directory=tmp_path / "export",
        is_confidence_included=False,
        scope=ExportScope.LISTED,
    )
    listed_indices: dict[Path, frozenset[int]] = {image_path: frozenset({0}) for image_path in workspace.image_paths}
    reply: ActionReply = workspace.export(ExportRequest(options, listed_indices, is_confidence_shown=True), False)
    assert reply.status == ActionStatus.REJECTED
    assert not workspace.is_busy
    assert not (tmp_path / "export").exists()
