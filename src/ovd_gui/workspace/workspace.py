from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import ClassVar

from open_vocabulary_detector import DetectionResult, DetectorSettings, PromptKind

from ..analysis import ProfileComparison, ResultStatistics
from ..detection import (
    BackgroundQueue,
    BatchDetectionRequest,
    BatchDetectionSummary,
    DetectionCatalog,
    DetectionFailure,
    DetectionFailureKind,
    DetectionOutcome,
    DetectionRequest,
    DetectorProfile,
    DetectorSession,
    LabeledPrompt,
    PromptChange,
    PromptSignature,
    ReferenceBoard,
    ResultLibrary,
)
from ..export import ExportScope, ExportSelection
from ..media import ImageCollection
from ..review import ClassThresholds
from ..storage import Session
from ..vocabulary import ClassDefinition
from .action_reply import ActionReply
from .action_status import ActionStatus
from .batch_job import BatchJob
from .batch_purpose import BatchPurpose
from .class_workbench import ClassWorkbench
from .detection_engine import DetectionEngine
from .export_plan import ExportPlan
from .export_report import ExportReport
from .export_request import ExportRequest
from .export_writer import ExportWriter
from .image_status import ImageStatus
from .model_selection import ModelSelection
from .model_selector import ModelSelector
from .notice import Notice
from .prompt_preparation import PromptPreparation
from .run_progress import RunProgress
from .scheduled_call import ScheduledCall
from .task_scheduler import TaskScheduler
from .workspace_observer import WorkspaceObserver
from .workspace_stores import WorkspaceStores
from .workspace_topic import WorkspaceTopic


class Workspace:
    """
    Everything the user works on, independent of any user interface: open images, classes, model settings, stored
    results and the detections running on the worker thread.

    The workspace lives on one owning thread, like the GUI thread of a desktop application: every method is called
    there, and the worker thread hands its outcomes back through the ``TaskScheduler``. Views follow it as
    ``WorkspaceObserver``s, told which parts changed and which notices to show.

    The latest result of every detected image is kept per detector profile (model, device, precision and
    thresholds), so detecting with another model adds results instead of replacing them. Open images without an
    up-to-date result of the model chosen in the settings are detected one by one in the background, the shown image
    first, unless the user pinned another model by selecting it; a failed background detection pauses the others
    until the user opens, shows or detects images or edits the classes. Detect, Detect All and Export are foreground
    runs, one at a time, which start as soon as the image being inferred in the background is done.

    Editing the classes keeps every result; images detected with other classes are reported as outdated. Results are
    saved shortly after every change, and the open images, the class list and the class minimums whenever they
    change.
    """

    DEFAULT_CLASS_NAMES: ClassVar[tuple[str, ...]] = ("person", "car", "dog")
    SAVE_DELAY_SECONDS: ClassVar[float] = 1.5

    def __init__(
        self,
        model_selector: ModelSelector,
        stores: WorkspaceStores,
        scheduler: TaskScheduler,
        session: DetectorSession | None = None,
    ) -> None:
        """
        Parameters
        ----------
        model_selector : ModelSelector
            Presets that can be chosen and the devices of this machine.
        stores : WorkspaceStores
            Data directories read at start and written after changes.
        scheduler : TaskScheduler
            Thread owning the workspace.
        session : DetectorSession | None, optional
            Session keeping the loaded model; a new one by default.
        """
        self._model_selector: ModelSelector = model_selector
        self._stores: WorkspaceStores = stores
        self._scheduler: TaskScheduler = scheduler
        self._observers: list[WorkspaceObserver] = []
        self._status_message: str = "Open images to start."
        self._status_serial: int = 0
        self._activity_message: str = ""
        self._summary: str = ""
        self._progress: RunProgress | None = None
        self._is_exporting: bool = False
        self._last_export: ExportReport | None = None
        self._pending_export: ExportRequest | None = None
        self._save_call: ScheduledCall | None = None
        self._image_paths: list[Path] = []
        self._current_path: Path | None = None
        self._result_library: ResultLibrary = self._load_results()
        self._shown_profile: DetectorProfile | None = None
        self._compared_profile: DetectorProfile | None = None
        self._class_thresholds: ClassThresholds = stores.class_threshold_store.load()
        self._workbench: ClassWorkbench = ClassWorkbench(stores.class_set_store)
        remembered_classes: tuple[ClassDefinition, ...] | None = stores.class_list_store.load()
        self._workbench.restore(
            tuple(ClassDefinition.named(name) for name in self.DEFAULT_CLASS_NAMES)
            if remembered_classes is None
            else remembered_classes
        )
        self._approved_skipped_classes: frozenset[str] = frozenset()
        self._background_queue: BackgroundQueue = BackgroundQueue(self._result_library)
        self._selection: ModelSelection = model_selector.default_selection()
        self._engine: DetectionEngine = DetectionEngine(scheduler, self, session)
        self._show_restored_results()

    @property
    def model_selector(self) -> ModelSelector:
        """
        Presets that can be chosen.

        Returns
        -------
        ModelSelector
            Selector given at construction.
        """
        return self._model_selector

    @property
    def stores(self) -> WorkspaceStores:
        """
        Data directories of the workspace.

        Returns
        -------
        WorkspaceStores
            Stores given at construction.
        """
        return self._stores

    @property
    def image_paths(self) -> tuple[Path, ...]:
        """
        Open images.

        Returns
        -------
        tuple[Path, ...]
            Image files in the order they were opened.
        """
        return tuple(self._image_paths)

    @property
    def current_path(self) -> Path | None:
        """
        Shown image.

        Returns
        -------
        Path | None
            ``None`` while no image is open.
        """
        return self._current_path

    @property
    def selection(self) -> ModelSelection:
        """
        Model chosen in the settings.

        Returns
        -------
        ModelSelection
            Preset and overrides.
        """
        return self._selection

    @property
    def workbench(self) -> ClassWorkbench:
        """
        Classes with their phrases and reference images.

        Returns
        -------
        ClassWorkbench
            Classes to detect; edit them through ``edit_classes``.
        """
        return self._workbench

    @property
    def result_library(self) -> ResultLibrary:
        """
        Stored results of every profile.

        Returns
        -------
        ResultLibrary
            Results; change them only through the workspace.
        """
        return self._result_library

    @property
    def shown_profile(self) -> DetectorProfile | None:
        """
        Profile whose results are shown.

        Returns
        -------
        DetectorProfile | None
            ``None`` while no results are shown.
        """
        return self._shown_profile

    @property
    def compared_profile(self) -> DetectorProfile | None:
        """
        Profile compared with the shown one.

        Returns
        -------
        DetectorProfile | None
            ``None`` while no profile is compared.
        """
        return self._compared_profile

    @property
    def class_thresholds(self) -> ClassThresholds:
        """
        Minimum confidence of each class.

        Returns
        -------
        ClassThresholds
            Default and per-class minimums.
        """
        return self._class_thresholds

    @property
    def status_message(self) -> str:
        """
        Latest status for the user.

        Returns
        -------
        str
            Message, possibly empty.
        """
        return self._status_message

    @property
    def status_serial(self) -> int:
        """
        Number of status messages posted so far, telling a repeated message from the previous one.

        Returns
        -------
        int
            Counter increased with every status message.
        """
        return self._status_serial

    @property
    def activity_message(self) -> str:
        """
        What the worker thread is doing.

        Returns
        -------
        str
            E.g. the model being loaded; empty while the worker is idle.
        """
        return self._activity_message

    @property
    def summary(self) -> str:
        """
        Model, prompt count, detection count and time of the latest detection of the shown image.

        Returns
        -------
        str
            One line; empty when the shown image was not detected since it was shown.
        """
        return self._summary

    @property
    def progress(self) -> RunProgress | None:
        """
        Progress of the batch in progress.

        Returns
        -------
        RunProgress | None
            ``None`` while no batch runs.
        """
        return self._progress

    @property
    def is_busy(self) -> bool:
        """
        Whether a foreground run or an export is in progress.

        Returns
        -------
        bool
            True while Detect, Detect All or an export runs.
        """
        return self._engine.is_busy or self._is_exporting

    @property
    def background_image_path(self) -> Path | None:
        """
        Image detected in the background now.

        Returns
        -------
        Path | None
            ``None`` while no background detection runs.
        """
        request: DetectionRequest | None = self._engine.background_request
        return None if request is None else request.image_path

    @property
    def last_export(self) -> ExportReport | None:
        """
        Latest finished export.

        Returns
        -------
        ExportReport | None
            ``None`` before the first export.
        """
        return self._last_export

    @property
    def is_image_prompt_supported(self) -> bool:
        """
        Whether the chosen backend takes reference images.

        Returns
        -------
        bool
            True for OWL-ViT and YOLOE.
        """
        return PromptKind.VISUAL in self._selection.backend.supported_prompt_kinds

    def add_observer(self, observer: WorkspaceObserver) -> None:
        """
        Follow the changes and notices of the workspace.

        Parameters
        ----------
        observer : WorkspaceObserver
            View to tell.
        """
        self._observers.append(observer)

    def remove_observer(self, observer: WorkspaceObserver) -> None:
        """
        Stop telling a view.

        Parameters
        ----------
        observer : WorkspaceObserver
            View added before; nothing happens otherwise.
        """
        if observer in self._observers:
            self._observers.remove(observer)

    def current_settings(self) -> DetectorSettings:
        """
        Settings of the model chosen now.

        Returns
        -------
        DetectorSettings
            Preset settings with the overrides applied.
        """
        return self._model_selector.settings_of(self._selection)

    def shown_catalog(self) -> DetectionCatalog | None:
        """
        Results of the shown profile.

        Returns
        -------
        DetectionCatalog | None
            ``None`` while no profile is shown.
        """
        shown_profile: DetectorProfile | None = self._shown_profile
        if shown_profile is None or shown_profile not in self._result_library:
            return None
        return self._result_library.catalog_of(shown_profile)

    def compared_catalog(self) -> DetectionCatalog | None:
        """
        Results of the compared profile.

        Returns
        -------
        DetectionCatalog | None
            ``None`` while no profile is compared.
        """
        compared_profile: DetectorProfile | None = self._compared_profile
        if compared_profile is None or compared_profile not in self._result_library:
            return None
        return self._result_library.catalog_of(compared_profile)

    def current_signature(self) -> PromptSignature:
        """
        What the current classes query.

        Returns
        -------
        PromptSignature
            Phrases and reference boxes of every class, whatever the model.
        """
        return self._workbench.reference_board.signature_of(self._workbench.classes)

    def outdated_changes(self) -> dict[Path, PromptChange]:
        """
        Open images whose shown result was detected with other classes than the current ones.

        Returns
        -------
        dict[Path, PromptChange]
            Change of every outdated open image.
        """
        if self._shown_profile is None or self._shown_profile not in self._result_library:
            return {}
        open_paths: frozenset[Path] = frozenset(self._image_paths)
        return {
            image_path: change
            for image_path, change in self._result_library.outdated_images(
                self._shown_profile, self.current_signature()
            ).items()
            if image_path in open_paths
        }

    def image_statuses(self) -> dict[Path, ImageStatus]:
        """
        State and kept detection count of every open image with the shown results.

        Returns
        -------
        dict[Path, ImageStatus]
            Status of every open image, in list order.
        """
        catalog: DetectionCatalog | None = self.shown_catalog()
        outdated_paths: frozenset[Path] = frozenset(self.outdated_changes())
        settings_profile: DetectorProfile = DetectorProfile.of(self.current_settings())
        return {
            image_path: ImageStatus.of(
                image_path,
                catalog,
                self._class_thresholds,
                is_outdated=image_path in outdated_paths,
                is_failed=self._background_queue.is_failed(settings_profile, image_path),
            )
            for image_path in self._image_paths
        }

    def statistics(self) -> ResultStatistics | None:
        """
        Per-class statistics of the shown results over the open images.

        Returns
        -------
        ResultStatistics | None
            ``None`` while no results are shown.
        """
        catalog: DetectionCatalog | None = self.shown_catalog()
        if catalog is None:
            return None
        return ResultStatistics.of(catalog, self.image_paths, self._workbench.class_names, self._class_thresholds)

    def comparison(self) -> ProfileComparison | None:
        """
        Class-by-class comparison of the shown and the compared results over the open images.

        Returns
        -------
        ProfileComparison | None
            ``None`` unless a profile is shown and another is compared.
        """
        shown_catalog: DetectionCatalog | None = self.shown_catalog()
        compared_catalog: DetectionCatalog | None = self.compared_catalog()
        if shown_catalog is None or compared_catalog is None:
            return None
        return ProfileComparison.between(shown_catalog, compared_catalog, self.image_paths, self._workbench.class_names)

    def open_paths(self, paths: Iterable[Path], is_first_shown: bool = True) -> None:
        """
        Add image files, or every image inside directories, to the open images.

        Parameters
        ----------
        paths : Iterable[Path]
            Image files and directories.
        is_first_shown : bool, optional
            Whether the first added image is shown; otherwise it is shown only when no image was shown. True by
            default.
        """
        collection: ImageCollection = ImageCollection.gather(paths, self._image_paths)
        if collection.is_empty:
            self._inform(collection.describe("No new images found"))
            return
        self._image_paths.extend(collection.image_paths)
        if is_first_shown or self._current_path is None:
            self._current_path = collection.image_paths[0]
            self._summary = ""
        added_count: int = len(collection.image_paths)
        self._inform(collection.describe(f"Added {added_count} image{'' if added_count == 1 else 's'}"))
        self._save_session()
        self._changed(WorkspaceTopic.STATE, WorkspaceTopic.DETECTIONS)
        self._resume_background_detection()

    def restore_session(self) -> None:
        """
        Open the images that were open at the end of the last session, and show the image shown then.

        Image files that no longer exist are skipped and counted in the status.
        """
        session: Session = self._stores.session_store.load()
        existing_paths: list[Path] = [image_path for image_path in session.image_paths if image_path.is_file()]
        missing_count: int = len(session.image_paths) - len(existing_paths)
        if not existing_paths:
            if missing_count:
                self._inform(f"None of the {missing_count} images of the last session exist any more.")
            return
        self.open_paths(existing_paths)
        if session.current_path is not None and session.current_path in self._image_paths:
            self.select_image(session.current_path)
        restored_count: int = len(existing_paths)
        missing_note: str = f" ({missing_count} missing skipped)" if missing_count else ""
        self._inform(
            f"Restored {restored_count} image{'' if restored_count == 1 else 's'} of the last session{missing_note}."
        )

    def close_images(self, image_paths: Iterable[Path]) -> None:
        """
        Close images, keeping their stored results; when the shown image is closed, the next remaining one is shown.

        Parameters
        ----------
        image_paths : Iterable[Path]
            Open images to close; others are ignored.
        """
        closed_paths: frozenset[Path] = frozenset(image_paths) & frozenset(self._image_paths)
        if not closed_paths:
            return
        if self._current_path in closed_paths:
            self._current_path = self._next_remaining_path(closed_paths)
            self._summary = ""
        self._image_paths = [image_path for image_path in self._image_paths if image_path not in closed_paths]
        closed_count: int = len(closed_paths)
        self._inform(f"Closed {closed_count} image{'' if closed_count == 1 else 's'}.")
        self._save_session()
        self._changed(WorkspaceTopic.STATE, WorkspaceTopic.DETECTIONS)
        self._resume_background_detection()

    def select_image(self, image_path: Path) -> None:
        """
        Show an open image; it is detected first when it has no up-to-date result.

        Parameters
        ----------
        image_path : Path
            Open image.

        Raises
        ------
        KeyError
            If the image is not open.
        """
        if image_path not in self._image_paths:
            raise KeyError(f"{image_path} is not open")
        if image_path != self._current_path:
            self._current_path = image_path
            self._summary = ""
            self._save_session()
            self._changed(WorkspaceTopic.STATE)
        self._resume_background_detection()

    def select_model(self, selection: ModelSelection) -> None:
        """
        Choose the model and options used by the next detections.

        Parameters
        ----------
        selection : ModelSelection
            Preset and overrides.

        Raises
        ------
        KeyError
            If the preset does not exist.
        ValueError
            If the device is not available on this machine.
        """
        if self.is_busy:
            raise ValueError("The model cannot be changed while a detection is running.")
        self._selection = self._model_selector.validated(selection)
        self._changed(WorkspaceTopic.STATE)

    def edit_classes(self, edit: Callable[[ClassWorkbench], object]) -> None:
        """
        Change the classes, phrases or reference images, then remember them and detect outdated images again.

        Parameters
        ----------
        edit : Callable[[ClassWorkbench], object]
            Edit applied to the workbench; an error it raises is passed on and nothing else happens.
        """
        edit(self._workbench)
        try:
            self._stores.class_list_store.save(self._workbench.classes)
        except OSError as error:
            self._inform(f"Could not remember the classes: {error}")
        self._background_queue.forget_failures()
        self._changed(WorkspaceTopic.STATE, WorkspaceTopic.DETECTIONS, WorkspaceTopic.CLASS_SETS)
        self._resume_background_detection()

    def edit_class_sets(self, edit: Callable[[ClassWorkbench], object]) -> None:
        """
        Change the saved class sets without changing the classes, e.g. rename, delete or import a set.

        Parameters
        ----------
        edit : Callable[[ClassWorkbench], object]
            Edit applied to the workbench; an error it raises is passed on.
        """
        edit(self._workbench)
        self._changed(WorkspaceTopic.STATE, WorkspaceTopic.CLASS_SETS)

    def detect_current(self, is_skipping_approved: bool) -> ActionReply:
        """
        Detect the shown image with the chosen model.

        Parameters
        ----------
        is_skipping_approved : bool
            Whether the user approved leaving out classes the model cannot query.

        Returns
        -------
        ActionReply
            Started, refused, or waiting for approval.
        """
        image_path: Path | None = self._current_path
        issue: str | None = self._readiness_issue("Open an image first." if image_path is None else None)
        if issue is not None or image_path is None:
            return self._reject(issue or "Open an image first.")
        preparation: PromptPreparation = self._prepare_prompt(is_skipping_approved)
        if preparation.labeled_prompt is None:
            return self._reply_without_prompt(preparation)
        settings: DetectorSettings = self.current_settings()
        self._switch_to(DetectorProfile.of(settings))
        self._engine.detect(
            DetectionRequest(settings=settings, image_path=image_path, labeled_prompt=preparation.labeled_prompt)
        )
        return ActionReply.done()

    def detect_all(self, is_skipping_approved: bool) -> ActionReply:
        """
        Detect every open image with the chosen model in one batch.

        Parameters
        ----------
        is_skipping_approved : bool
            Whether the user approved leaving out classes the model cannot query.

        Returns
        -------
        ActionReply
            Started, refused, or waiting for approval.
        """
        issue: str | None = self._readiness_issue(self._missing_images_issue())
        if issue is not None:
            return self._reject(issue)
        return self._start_batch(self.image_paths, is_skipping_approved, None)

    def update_outdated(self, is_skipping_approved: bool) -> ActionReply:
        """
        Detect again the open images whose shown result was detected with other classes.

        Parameters
        ----------
        is_skipping_approved : bool
            Whether the user approved leaving out classes the model cannot query.

        Returns
        -------
        ActionReply
            Started, refused, or waiting for approval.
        """
        outdated_paths: tuple[Path, ...] = tuple(self.outdated_changes())
        issue: str | None = self._readiness_issue(None if outdated_paths else "No outdated images to update.")
        if issue is not None:
            return self._reject(issue)
        shown_profile: DetectorProfile | None = self._shown_profile
        if shown_profile is not None and not self._is_selected_in_settings(shown_profile):
            return self._reject(
                f"The outdated images were detected with {shown_profile.model_name} "
                + f"({shown_profile.options_text}); choose these model settings to update them."
            )
        return self._start_batch(outdated_paths, is_skipping_approved, None)

    def cancel_batch(self) -> None:
        """
        Ask the running batch, if any, to stop before its next image.
        """
        self._engine.cancel_batch()

    def export_plan(self) -> ExportPlan:
        """
        What an export would write now.

        Returns
        -------
        ExportPlan
            Model, image counts and why the export cannot start, if it cannot.
        """
        profile: DetectorProfile = self._shown_profile or DetectorProfile.of(self.current_settings())
        pending_paths: tuple[Path, ...] = self._pending_paths_of(profile)
        issue: str | None = self._missing_images_issue()
        if issue is None and self.is_busy:
            issue = "A detection is already running."
        if issue is None and pending_paths and not self._is_selected_in_settings(profile):
            issue = (
                f"{len(pending_paths)} images have no up-to-date result of {profile.model_name} "
                + f"({profile.options_text}); choose these model settings to detect them before exporting."
            )
        return ExportPlan(
            profile=profile,
            image_count=len(self._image_paths),
            pending_count=len(pending_paths),
            issue=issue or "",
        )

    def export(self, request: ExportRequest, is_skipping_approved: bool) -> ActionReply:
        """
        Write the stored results of the shown model, detecting the open images without an up-to-date result first.

        Exporting only the listed detections is refused while an image has no up-to-date result, because the
        detection table has not listed the detections it is about to get.

        Parameters
        ----------
        request : ExportRequest
            Options chosen by the user.
        is_skipping_approved : bool
            Whether the user approved leaving out classes the model cannot query.

        Returns
        -------
        ActionReply
            Started, refused, or waiting for approval.
        """
        plan: ExportPlan = self.export_plan()
        if plan.issue:
            return self._reject(plan.issue)
        if request.options.scope == ExportScope.LISTED and plan.pending_count > 0:
            return self._reject(
                f"Only listed detections can be exported once every image is detected; {plan.pending_count} "
                + "images have no up-to-date result. Run Detect All or Update outdated first, or export every "
                + "detection."
            )
        if plan.pending_count == 0:
            self._write_export(plan.profile, request, "")
            return ActionReply.done()
        issue: str | None = self._readiness_issue(None)
        if issue is not None:
            return self._reject(issue)
        return self._start_batch(self._pending_paths_of(plan.profile), is_skipping_approved, request)

    def select_profile(self, profile: DetectorProfile) -> None:
        """
        Show the results of a stored profile and keep background detection from replacing it.

        Parameters
        ----------
        profile : DetectorProfile
            Stored profile.

        Raises
        ------
        KeyError
            If the profile is not stored.
        """
        self._result_library.catalog_of(profile)
        self._background_queue.pin()
        self._display_profile(profile)
        self._resume_background_detection()

    def remove_profile(self, profile: DetectorProfile) -> None:
        """
        Forget the results of one profile.

        Parameters
        ----------
        profile : DetectorProfile
            Profile to forget; nothing happens if it is not stored.
        """
        self._result_library.remove(profile)
        self._schedule_save()
        if profile == self._compared_profile:
            self._compared_profile = None
        if profile == self._shown_profile:
            remaining_profiles: tuple[DetectorProfile, ...] = self._result_library.profiles
            self._display_profile(remaining_profiles[-1] if remaining_profiles else None)
            return
        self._changed(WorkspaceTopic.STATE)

    def clear_results(self) -> None:
        """
        Forget every stored result.
        """
        self._result_library.clear()
        self._compared_profile = None
        self._display_profile(None)
        self._schedule_save()

    def compare_with(self, profile: DetectorProfile | None) -> None:
        """
        Compare the shown results with another stored profile, or stop comparing.

        Parameters
        ----------
        profile : DetectorProfile | None
            Stored profile other than the shown one; ``None`` stops comparing.
        """
        is_comparable: bool = profile is not None and profile in self._result_library and profile != self._shown_profile
        self._compared_profile = profile if is_comparable else None
        self._changed(WorkspaceTopic.STATE)

    def set_accepted(self, detection_indices: Mapping[Path, Iterable[int]], is_accepted: bool) -> None:
        """
        Keep or reject detections of the shown results.

        Parameters
        ----------
        detection_indices : Mapping[Path, Iterable[int]]
            Indices of the detections in the result of each image.
        is_accepted : bool
            True to keep them, False to reject them.

        Raises
        ------
        KeyError
            If no results are shown or an image has not been detected.
        IndexError
            If an index is outside the result of its image.
        """
        catalog: DetectionCatalog | None = self.shown_catalog()
        if catalog is None:
            raise KeyError("No results are shown.")
        for image_path, indices in detection_indices.items():
            catalog.set_accepted(image_path, indices, is_accepted)
        self._schedule_save()
        self._changed(WorkspaceTopic.STATE, WorkspaceTopic.DETECTIONS)

    def set_class_thresholds(self, class_thresholds: ClassThresholds) -> None:
        """
        Change the minimum confidence of the classes and remember it.

        Parameters
        ----------
        class_thresholds : ClassThresholds
            Default and per-class minimums.
        """
        self._class_thresholds = class_thresholds
        try:
            self._stores.class_threshold_store.save(class_thresholds)
        except OSError as error:
            self._inform(f"Could not save the class minimums: {error}")
        self._changed(WorkspaceTopic.STATE)

    def save_results(self) -> None:
        """
        Write the stored results to the data directory now, reporting a failure in the status.
        """
        if self._save_call is not None:
            self._save_call.cancel()
            self._save_call = None
        try:
            self._stores.result_store.save(self._result_library)
        except OSError as error:
            self._inform(f"Could not save the results: {error}")

    def shutdown(self) -> None:
        """
        Stop the worker thread and write the results and the open images.

        Outcomes the worker reported but the scheduler has not delivered yet are lost; an owner thread that keeps
        delivering them while the worker stops calls ``stop_detection``, ``join_detection`` and ``save`` instead.
        """
        self.stop_detection()
        self.join_detection()
        self.save()

    def stop_detection(self) -> None:
        """
        Cancel the running batch and ask the worker thread to quit after the current image, without waiting.
        """
        self._engine.stop()

    def join_detection(self) -> None:
        """
        Wait until the worker thread has quit; the only method safe to call from a thread other than the owner.

        Raises
        ------
        RuntimeError
            If ``stop_detection`` was not called first.
        """
        self._engine.join()

    def save(self) -> None:
        """
        Write the results and the open images now.
        """
        self.save_results()
        self._save_session()

    def on_busy_changed(self, is_busy: bool) -> None:
        """
        Follow the foreground runs of the engine.

        Parameters
        ----------
        is_busy : bool
            Whether a foreground run is in progress now.
        """
        if not is_busy:
            self._progress = None
            self._clear_activity_when_idle()
        self._changed(WorkspaceTopic.STATE)
        if not is_busy:
            self._resume_background_detection()

    def on_status_changed(self, message: str) -> None:
        """
        Show what the worker thread is doing.

        Parameters
        ----------
        message : str
            Progress message.
        """
        self._activity_message = message
        self._changed(WorkspaceTopic.STATE)

    def on_succeeded(self, outcome: DetectionOutcome) -> None:
        """
        Store the result of Detect.

        Parameters
        ----------
        outcome : DetectionOutcome
            Result with its request and timing.
        """
        self._record_outcome(outcome)
        self._inform("Done.")

    def on_failed(self, failure: DetectionFailure) -> None:
        """
        Report a failed Detect.

        Parameters
        ----------
        failure : DetectionFailure
            Why it failed.
        """
        self._alert("Detection failed", failure.message)

    def on_background_succeeded(self, outcome: DetectionOutcome) -> None:
        """
        Store a background result and detect the next image.

        Parameters
        ----------
        outcome : DetectionOutcome
            Result with its request and timing.
        """
        self._record_outcome(outcome)
        self._clear_activity_when_idle()
        self._detect_in_background()

    def on_background_failed(self, request: DetectionRequest, failure: DetectionFailure) -> None:
        """
        Leave an image alone after its background detection failed.

        Parameters
        ----------
        request : DetectionRequest
            Request that failed.
        failure : DetectionFailure
            Why it failed: an unreadable file is skipped, a model error pauses background detection.
        """
        self._background_queue.record_failure(request, failure)
        self._clear_activity_when_idle()
        self._changed(WorkspaceTopic.STATE)
        match failure.kind:
            case DetectionFailureKind.UNREADABLE_IMAGE:
                self._detect_in_background()
            case DetectionFailureKind.DETECTION_ERROR:
                self._inform(f"Background detection of {request.image_path.name} failed: {failure.message}")

    def on_batch_progressed(self, job: BatchJob, processed_count: int, total_count: int) -> None:
        """
        Show the progress of the running batch.

        Parameters
        ----------
        job : BatchJob
            Running batch.
        processed_count : int
            Images processed so far.
        total_count : int
            Images in the batch.
        """
        self._progress = RunProgress(
            title=job.purpose.title,
            processed_count=processed_count,
            total_count=total_count,
            is_blocking=job.purpose.is_blocking,
        )
        self._changed(WorkspaceTopic.STATE)

    def on_batch_image_detected(self, job: BatchJob, image_path: Path, result: DetectionResult) -> None:
        """
        Store the result of one image of the running batch.

        Parameters
        ----------
        job : BatchJob
            Running batch.
        image_path : Path
            Detected image.
        result : DetectionResult
            Detections of the image.
        """
        self._record_result(DetectorProfile.of(job.request.settings), image_path, result, job.request.labeled_prompt)

    def on_batch_finished(self, job: BatchJob, summary: BatchDetectionSummary) -> None:
        """
        Report a finished batch, and write the export it was run for.

        Parameters
        ----------
        job : BatchJob
            Finished batch.
        summary : BatchDetectionSummary
            Detected count, skipped files and whether it was cancelled.
        """
        self._progress = None
        skipped_note: str = (
            f" ({len(summary.unreadable_paths)} unreadable images skipped)" if summary.unreadable_paths else ""
        )
        pending_export: ExportRequest | None = self._pending_export
        self._pending_export = None
        match job.purpose:
            case BatchPurpose.DETECT_ALL:
                outcome_text: str = (
                    f"Detect All stopped after {summary.detected_count} images"
                    if summary.is_cancelled
                    else f"Detected {summary.detected_count} images"
                )
                self._inform(f"{outcome_text}{skipped_note}.")
            case BatchPurpose.EXPORT:
                if summary.is_cancelled:
                    self._inform(f"Export cancelled after {summary.detected_count} images.")
                elif pending_export is not None:
                    self._write_export(DetectorProfile.of(job.request.settings), pending_export, skipped_note)

    def on_batch_failed(self, job: BatchJob, message: str) -> None:
        """
        Report a batch stopped by an error.

        Parameters
        ----------
        job : BatchJob
            Failed batch.
        message : str
            Error message.
        """
        self._progress = None
        self._pending_export = None
        self._alert(f"{job.purpose.title} failed", message)

    def _changed(self, *topics: WorkspaceTopic) -> None:
        changed_topics: frozenset[WorkspaceTopic] = frozenset(topics)
        for observer in tuple(self._observers):
            observer.on_changed(changed_topics)

    def _inform(self, message: str) -> None:
        self._status_message = message
        self._status_serial += 1
        self._changed(WorkspaceTopic.STATE)

    def _alert(self, title: str, message: str) -> None:
        self._inform(f"{title}.")
        notice: Notice = Notice.error(title, message)
        for observer in tuple(self._observers):
            observer.on_notice(notice)

    def _reject(self, message: str) -> ActionReply:
        self._inform(message)
        return ActionReply.rejected(message)

    def _clear_activity_when_idle(self) -> None:
        if self._engine.is_idle:
            self._activity_message = ""

    def _load_results(self) -> ResultLibrary:
        try:
            return self._stores.result_store.load()
        except (OSError, ValueError) as error:
            self._status_message = f"Could not restore the saved results: {error}"
            return ResultLibrary()

    def _show_restored_results(self) -> None:
        profiles: tuple[DetectorProfile, ...] = self._result_library.profiles
        if not profiles:
            return
        settings_profile: DetectorProfile = DetectorProfile.of(self.current_settings())
        self._shown_profile = settings_profile if settings_profile in profiles else profiles[-1]

    def _next_remaining_path(self, closed_paths: frozenset[Path]) -> Path | None:
        if self._current_path is None:
            return None
        current_index: int = self._image_paths.index(self._current_path)
        following: list[Path] = [path for path in self._image_paths[current_index:] if path not in closed_paths]
        preceding: list[Path] = [path for path in self._image_paths[:current_index] if path not in closed_paths]
        if following:
            return following[0]
        return preceding[-1] if preceding else None

    def _save_session(self) -> None:
        try:
            self._stores.session_store.save(
                Session(image_paths=tuple(self._image_paths), current_path=self._current_path)
            )
        except OSError as error:
            self._inform(f"Could not save the open images: {error}")

    def _schedule_save(self) -> None:
        if self._save_call is not None:
            self._save_call.cancel()
        self._save_call = self._scheduler.call_later(self.SAVE_DELAY_SECONDS, self.save_results)

    def _resume_background_detection(self) -> None:
        self._background_queue.resume()
        self._detect_in_background()

    def _detect_in_background(self) -> None:
        if not self._workbench.classes or self._is_exporting:
            return
        if self._engine.is_busy:
            if self._current_path is not None:
                self._engine.prioritize(self._current_path)
            return
        settings: DetectorSettings = self.current_settings()
        profile: DetectorProfile = DetectorProfile.of(settings)
        image_path: Path | None = self._background_queue.next_image(
            profile, self._shown_profile, self.current_signature(), self._current_path, self._image_paths
        )
        if image_path is None:
            return
        labeled_prompt: LabeledPrompt | None = self._build_background_prompt()
        if labeled_prompt is None:
            return
        self._switch_to(profile)
        self._engine.detect_in_background(
            DetectionRequest(settings=settings, image_path=image_path, labeled_prompt=labeled_prompt)
        )
        self._changed(WorkspaceTopic.STATE)

    def _readiness_issue(self, missing_image_issue: str | None) -> str | None:
        if self.is_busy:
            return "A detection is already running."
        if missing_image_issue is not None:
            return missing_image_issue
        if not self._workbench.classes:
            return "Add at least one class to detect."
        return None

    def _missing_images_issue(self) -> str | None:
        return None if self._image_paths else "Open images first."

    def _is_selected_in_settings(self, profile: DetectorProfile) -> bool:
        return DetectorProfile.of(self.current_settings()) == profile

    def _pending_paths_of(self, profile: DetectorProfile) -> tuple[Path, ...]:
        signature: PromptSignature = self.current_signature()
        return tuple(
            image_path
            for image_path in self._image_paths
            if not self._is_up_to_date(self._result_library.prompt_change_of(profile, image_path, signature))
        )

    @staticmethod
    def _is_up_to_date(change: PromptChange | None) -> bool:
        return change is not None and change.is_unchanged

    def _prepare_prompt(self, is_skipping_approved: bool) -> PromptPreparation:
        supported_kinds: frozenset[PromptKind] = self._selection.backend.supported_prompt_kinds
        definitions: tuple[ClassDefinition, ...] = self._workbench.classes
        board: ReferenceBoard = self._workbench.reference_board
        skipped_names: tuple[str, ...] = board.reference_only_classes(definitions, supported_kinds)
        if skipped_names and len(skipped_names) < len(definitions):
            if frozenset(skipped_names) != self._approved_skipped_classes:
                if not is_skipping_approved:
                    return PromptPreparation(labeled_prompt=None, unapproved_class_names=skipped_names)
                self._approved_skipped_classes = frozenset(skipped_names)
            definitions = tuple(definition for definition in definitions if definition.name not in skipped_names)
        issue: str | None = board.prompt_issue(definitions, supported_kinds)
        if issue is not None:
            return PromptPreparation(labeled_prompt=None, issue=issue)
        return PromptPreparation(labeled_prompt=board.build_prompt(definitions, supported_kinds))

    def _reply_without_prompt(self, preparation: PromptPreparation) -> ActionReply:
        if preparation.unapproved_class_names:
            listed_names: str = ", ".join(preparation.unapproved_class_names)
            return ActionReply(
                status=ActionStatus.NEEDS_APPROVAL,
                message=f"{self._selection.backend.value} does not take reference images, so these classes have "
                + f"no usable query: {listed_names}. Detect the other classes without them?",
                skipped_class_names=preparation.unapproved_class_names,
            )
        return self._reject(preparation.issue)

    def _build_background_prompt(self) -> LabeledPrompt | None:
        supported_kinds: frozenset[PromptKind] = self._selection.backend.supported_prompt_kinds
        definitions: tuple[ClassDefinition, ...] = self._workbench.classes
        board: ReferenceBoard = self._workbench.reference_board
        skipped_names: tuple[str, ...] = board.reference_only_classes(definitions, supported_kinds)
        if skipped_names and frozenset(skipped_names) != self._approved_skipped_classes:
            return None
        kept_definitions: tuple[ClassDefinition, ...] = tuple(
            definition for definition in definitions if definition.name not in skipped_names
        )
        if board.prompt_issue(kept_definitions, supported_kinds) is not None:
            return None
        return board.build_prompt(kept_definitions, supported_kinds)

    def _start_batch(
        self, image_paths: tuple[Path, ...], is_skipping_approved: bool, export_request: ExportRequest | None
    ) -> ActionReply:
        preparation: PromptPreparation = self._prepare_prompt(is_skipping_approved)
        if preparation.labeled_prompt is None:
            return self._reply_without_prompt(preparation)
        request: BatchDetectionRequest = BatchDetectionRequest(
            settings=self.current_settings(), labeled_prompt=preparation.labeled_prompt, image_paths=image_paths
        )
        self._switch_to(DetectorProfile.of(request.settings))
        self._pending_export = export_request
        job: BatchJob = (
            BatchJob.detect_all(request) if export_request is None else BatchJob.export(request, export_request.options)
        )
        self._progress = RunProgress(
            title=job.purpose.title,
            processed_count=0,
            total_count=len(image_paths),
            is_blocking=job.purpose.is_blocking,
        )
        self._engine.detect_batch(job)
        return ActionReply.done()

    def _record_outcome(self, outcome: DetectionOutcome) -> None:
        self._record_result(
            DetectorProfile.of(outcome.request.settings),
            outcome.request.image_path,
            outcome.result,
            outcome.request.labeled_prompt,
        )
        if self._current_path != outcome.request.image_path:
            return
        load_note: str = " (model loaded)" if outcome.is_model_reloaded else ""
        prompt_kinds: str = "+".join(sorted(kind.value for kind in outcome.result.prompt.kinds))
        self._summary = (
            f"{outcome.request.settings.backend.value} | {outcome.request.settings.weights_path} | "
            + f"{len(outcome.result.prompt.queries)} {prompt_kinds} prompts | "
            + f"{len(outcome.result)} detections | {outcome.inference_seconds * 1000:.0f} ms{load_note}"
        )
        self._changed(WorkspaceTopic.STATE)

    def _record_result(
        self, profile: DetectorProfile, image_path: Path, result: DetectionResult, labeled_prompt: LabeledPrompt
    ) -> None:
        self._result_library.record(profile, image_path, result, labeled_prompt)
        self._schedule_save()
        if profile == self._shown_profile and image_path in self._image_paths:
            self._changed(WorkspaceTopic.STATE, WorkspaceTopic.DETECTIONS)
        else:
            self._changed(WorkspaceTopic.STATE)

    def _switch_to(self, profile: DetectorProfile) -> None:
        self._background_queue.unpin()
        self._result_library.add(profile)
        if profile != self._shown_profile:
            self._display_profile(profile)
        self._changed(WorkspaceTopic.STATE)

    def _display_profile(self, profile: DetectorProfile | None) -> None:
        self._shown_profile = profile
        if self._compared_profile == profile:
            self._compared_profile = None
        self._summary = ""
        self._changed(WorkspaceTopic.STATE, WorkspaceTopic.DETECTIONS)

    def _write_export(self, profile: DetectorProfile, request: ExportRequest, skipped_note: str) -> None:
        catalog: DetectionCatalog = self._result_library.add(profile)
        selection: ExportSelection = ExportSelection(
            class_thresholds=self._class_thresholds,
            minimum_confidence=request.options.minimum_confidence,
            listed_indices=(
                request.listed_indices
                if request.options.scope == ExportScope.LISTED and profile == self._shown_profile
                else None
            ),
        )
        selected_results: dict[Path, DetectionResult] = {}
        for image_path in self._image_paths:
            selected_result: DetectionResult | None = selection.selected_result(catalog, image_path)
            if selected_result is not None:
                selected_results[image_path] = selected_result
        class_names: tuple[str, ...] = self._workbench.class_names
        writer: ExportWriter = ExportWriter(request.is_confidence_shown)
        self._is_exporting = True
        self._activity_message = f"Writing {request.options.annotation_format.display_name} files ..."
        self._changed(WorkspaceTopic.STATE)
        self._scheduler.run_blocking(
            lambda: writer.write(selected_results, request.options, class_names),
            lambda report: self._on_export_written(report, skipped_note),
            self._on_export_failed,
        )

    def _on_export_written(self, report: ExportReport, skipped_note: str) -> None:
        self._is_exporting = False
        self._last_export = report
        self._clear_activity_when_idle()
        image_note: str = (
            "" if report.annotated_image_count is None else f", {report.annotated_image_count} images with boxes"
        )
        self._inform(
            f"Exported {report.format_name}: {report.image_count} images, {report.detection_count} detections, "
            + f"{report.file_count} files{image_note} to {report.output_directory}{skipped_note}."
        )
        self._resume_background_detection()

    def _on_export_failed(self, error: Exception) -> None:
        self._is_exporting = False
        self._clear_activity_when_idle()
        self._alert("Export failed", str(error))
        self._resume_background_detection()
