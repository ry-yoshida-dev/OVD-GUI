from collections.abc import Callable
from pathlib import Path

import pytest

from ovd_gui.detection import BatchDetectionSummary, ResultLibrary
from ovd_gui.workspace import ActionStatus, BatchJob, Workspace, WorkspaceStores

from .conftest import ManualScheduler


def test_a_foreground_run_waits_for_the_background_detection_in_progress(
    workspace: Workspace, image_directory: Path, wait_until_idle: Callable[[], None]
) -> None:
    workspace.open_paths([image_directory])
    background_image: Path | None = workspace.background_image_path
    assert background_image is not None
    workspace.detect_all(is_skipping_approved=False)
    assert workspace.is_busy
    wait_until_idle()
    assert workspace.status_message == "Detected 3 images."


def test_cancelled_batch_stops_before_its_next_image(
    workspace: Workspace, image_directory: Path, wait_until_idle: Callable[[], None]
) -> None:
    workspace.open_paths([image_directory])
    wait_until_idle()
    workspace.detect_all(is_skipping_approved=False)
    workspace.cancel_batch()
    wait_until_idle()
    assert workspace.status_message.startswith("Detect All stopped after")


def test_engine_is_idle_again_when_the_listener_raises(
    workspace: Workspace,
    image_directory: Path,
    wait_until_idle: Callable[[], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace.open_paths([image_directory])
    wait_until_idle()

    def raise_error(job: BatchJob, summary: BatchDetectionSummary) -> None:
        raise RuntimeError("listener failed")

    monkeypatch.setattr(workspace, "on_batch_finished", raise_error)
    workspace.detect_all(is_skipping_approved=False)
    with pytest.raises(RuntimeError, match="listener failed"):
        wait_until_idle()
    assert not workspace.is_busy
    monkeypatch.undo()
    assert workspace.detect_all(is_skipping_approved=False).status == ActionStatus.DONE
    wait_until_idle()


def test_outcomes_delivered_after_the_worker_stops_are_saved(
    workspace: Workspace, image_directory: Path, stores: WorkspaceStores, scheduler: ManualScheduler
) -> None:
    workspace.open_paths([image_directory])
    background_image: Path | None = workspace.background_image_path
    assert background_image is not None
    workspace.stop_detection()
    workspace.join_detection()
    scheduler.pump_until(lambda: True)
    assert workspace.background_image_path is None
    workspace.save()
    library: ResultLibrary = stores.result_store.load()
    assert any(library.catalog_of(profile).result_of(background_image) for profile in library.profiles)
