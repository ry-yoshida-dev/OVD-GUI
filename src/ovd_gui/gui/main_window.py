from pathlib import Path

from open_vocabulary_detector import DetectionResult, DetectorSettings, PromptKind
from PySide6.QtCore import QMimeData, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QToolButton,
    QWidget,
)

from ..analysis import ProfileComparison, ResultStatistics
from ..detection import (
    BackgroundQueue,
    BatchDetectionRequest,
    BatchDetectionSummary,
    DetectionCatalog,
    DetectionFailure,
    DetectionFailureKind,
    DetectionOutcome,
    DetectionRecord,
    DetectionRequest,
    DetectorProfile,
    DeviceAvailability,
    LabeledPrompt,
    PromptChange,
    PromptSignature,
    ReferenceBoard,
    ResultLibrary,
)
from ..export import AnnotatedImageWriter, DetectionArchive, ExportOptions, ExportScope, ExportSelection
from ..media import ImageCollection, LoadedImage
from ..preset import PresetCatalog
from ..review import ClassThresholds
from ..storage import ClassSetStore, ClassThresholdStore, ResultStore, Session, SessionStore
from ..vocabulary import ClassDefinition, ClassListStore
from .class_palette import ClassPalette
from .execution import BatchJob, BatchProgressDialog, BatchPurpose, DetectionRunner, RunProgressIndicator
from .export_dialog import ExportDialog
from .intake import DropOverlay, DropZone
from .prompt import ClassEditor
from .sidebar import CollapsibleSection, ImageListPanel, ImageStatus, SectionStack, SettingsPanel
from .statistics import StatisticsWindow
from .table import ProfilePanel, ResultPanel
from .viewer import DetectionOverlay, DisplayMenu, ImageCanvas


class MainWindow(QMainWindow):
    """
    Main window: model settings, class editor and image list on the left, image with detections in the center,
    detection table on the right.

    The latest result of every detected image is kept, so switching images shows its boxes again without detecting,
    and the detection table can list, filter and sort the detections of every image at once. Detect All detects
    every open image on the worker thread in the background: images, classes and the table stay usable, results
    appear as each image finishes, and the status bar shows its progress with a Cancel button. Selecting a detection
    of another image in the table opens that image.

    Open images are detected one by one in the background when the current model has no up-to-date result for
    them, without blocking the window: the shown image first, then the other images in list order. An image whose
    background detection failed is not retried by itself for the same model until the classes change, and a failure
    pauses the detection of the other images until the user opens, shows or detects images or edits the classes.
    What the user does on screen comes first: Detect, Detect All and Export start as soon as the image being
    inferred in the background is done, a newly shown image is detected before the other images, an image shown
    while Detect All runs is detected next in the batch, and no background detection replaces the results of
    another model the user selected in the model table.

    Results are kept per detector profile (model, device, precision and thresholds): detecting with another model
    adds a row to the model table above the detection table instead of replacing earlier results, and selecting a
    row there shows that model's boxes and detections again, so models can be compared without detecting again.

    Every class is queried by its phrases and, with a backend that takes image prompts (OWL-ViT, YOLOE), by its
    reference images. Detections are reported under the class and name the query that matched.

    Editing the classes, phrases or reference images keeps every stored result. Images detected with other classes
    than the current ones are marked outdated in the detection table and counted in the model table, and are
    detected again in the background, the shown image first; Update Outdated detects them again in one batch.

    Images and folders can be dropped anywhere on the window; while dragging, an overlay previews what the drop
    adds. Until an image is open, the center shows a drop zone instead of the image. The image list marks every image
    detected, outdated, failed or not analyzed with the shown model and counts its kept detections; selected images
    can be closed. Left and Right (or Page Up and Page Down) on the image or the list show the previous or next image.

    Detections are reviewed in the detection table: unchecking ``Keep`` rejects a detection, and the minimum
    confidence of each class, set in the statistics window, hides the detections below it. The image draws only the
    detections the table lists, so its column filters also filter the boxes; the View menu chooses labels,
    confidences, rejected boxes, line width and fill. The statistics window counts the detections of each class over
    the open images with a confidence histogram, and compares the shown model with another stored one, whose boxes
    are then drawn dotted over the image.

    Export writes the stored results of the shown model in the chosen annotation format, leaving out rejected
    detections and those below the class minimums (optionally also those hidden by the table filters or below an
    export minimum). Open images without an up-to-date result are detected first on the worker thread, blocking the
    window with a cancellable progress dialog until the files are written.

    Export can also save every exported image with its exported detections drawn, and the detection table saves its
    listed detections as a CSV file.

    Results, with the rejected detections, are saved in the data directory shortly after every change and when the
    window closes, and restored at the next start for the image files that have not changed; the class minimums are
    saved as well. The open images and the shown one are remembered whenever the image list changes and when the
    window closes; ``restore_session`` opens them again.
    """

    WINDOW_TITLE = "OVD GUI"
    DEFAULT_CLASS_NAMES: tuple[str, ...] = ("person", "car", "dog")
    DEFAULT_SIDEBAR_WIDTH = 320
    DEFAULT_PROFILE_PANEL_HEIGHT = 150
    DEFAULT_RESULT_PANEL_HEIGHT = 650
    SIDEBAR_INDEX = 0
    CANVAS_INDEX = 1
    RESULT_INDEX = 2
    NOTICE_TIMEOUT_MILLISECONDS = 3000
    SAVE_DELAY_MILLISECONDS = 1500
    REVIEW_REFRESH_DELAY_MILLISECONDS = 50

    def __init__(
        self,
        catalog: PresetCatalog,
        class_list_store: ClassListStore,
        class_set_store: ClassSetStore,
        device_availability: DeviceAvailability,
        result_store: ResultStore,
        class_threshold_store: ClassThresholdStore,
        session_store: SessionStore,
    ) -> None:
        """
        Parameters
        ----------
        catalog : PresetCatalog
            Presets offered in the model settings.
        class_list_store : ClassListStore
            Data directory remembering the class list between runs.
        class_set_store : ClassSetStore
            Data directory holding the saved class sets with their reference images.
        device_availability : DeviceAvailability
            GPU backends of this machine, deciding which model settings can be chosen.
        result_store : ResultStore
            Data directory remembering the detection results between runs.
        class_threshold_store : ClassThresholdStore
            Data directory remembering the minimum confidence of each class between runs.
        session_store : SessionStore
            Data directory remembering the open images between runs.
        """
        super().__init__()
        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(1400, 850)
        self.setAcceptDrops(True)

        self._result_store: ResultStore = result_store
        self._class_threshold_store: ClassThresholdStore = class_threshold_store
        self._session_store: SessionStore = session_store
        self._restore_notice: str | None = None
        self._current_image: LoadedImage | None = None
        self._result_library: ResultLibrary = self._load_results()
        self._shown_profile: DetectorProfile | None = None
        self._compared_profile: DetectorProfile | None = None
        self._class_thresholds: ClassThresholds = class_threshold_store.load()
        self._reference_board: ReferenceBoard = ReferenceBoard()
        self._approved_skipped_classes: frozenset[str] = frozenset()
        self._background_queue: BackgroundQueue = BackgroundQueue(self._result_library)

        palette: ClassPalette = ClassPalette()
        self._settings_panel: SettingsPanel = SettingsPanel(catalog, device_availability)
        self._image_list: ImageListPanel = ImageListPanel()
        self._canvas: ImageCanvas = ImageCanvas(palette)
        self._canvas.setAcceptDrops(False)
        self._drop_zone: DropZone = DropZone()
        self._center_stack: QStackedWidget = QStackedWidget()
        self._center_stack.addWidget(self._drop_zone)
        self._center_stack.addWidget(self._canvas)
        self._result_panel: ResultPanel = ResultPanel(palette)
        self._result_panel.set_class_thresholds(self._class_thresholds)
        self._profile_panel: ProfilePanel = ProfilePanel()
        self._result_splitter: QSplitter = QSplitter(Qt.Orientation.Vertical)
        self._class_editor: ClassEditor = ClassEditor(palette, class_list_store, class_set_store, self._reference_board)
        self._class_editor.restore(tuple(ClassDefinition.named(name) for name in self.DEFAULT_CLASS_NAMES))
        self._detect_button: QPushButton = QPushButton("Detect")
        self._detect_all_button: QPushButton = QPushButton("Detect All")
        self._summary_label: QLabel = QLabel()
        self._export_dialog: ExportDialog = ExportDialog(self)
        self._export_action: QAction = QAction("Export…", self)
        self._statistics_window: StatisticsWindow = StatisticsWindow(palette, self)
        self._display_menu: DisplayMenu = DisplayMenu(self._canvas.display_options, self)
        self._previous_image_action: QAction = QAction("◀", self)
        self._next_image_action: QAction = QAction("▶", self)
        self._save_timer: QTimer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(self.SAVE_DELAY_MILLISECONDS)
        self._review_refresh_timer: QTimer = QTimer(self)
        self._review_refresh_timer.setSingleShot(True)
        self._review_refresh_timer.setInterval(self.REVIEW_REFRESH_DELAY_MILLISECONDS)

        self._runner: DetectionRunner = DetectionRunner(self)
        self._batch_progress_dialog: BatchProgressDialog = BatchProgressDialog(self._runner, self)
        self._run_progress_indicator: RunProgressIndicator = RunProgressIndicator(self._runner)

        self._splitter: QSplitter = QSplitter(Qt.Orientation.Horizontal)
        self._sidebar: SectionStack = SectionStack()
        self._images_section: CollapsibleSection = self._build_layout()
        self._drop_overlay: DropOverlay = DropOverlay(self)
        self._is_drop_acceptable: bool = False
        self._build_toolbar()
        self._connect_signals()

        self.statusBar().addPermanentWidget(self._summary_label)
        self.statusBar().addPermanentWidget(self._run_progress_indicator)
        self.statusBar().showMessage(self._restore_notice or "Drop images or folders to start.")
        self._show_restored_results()

    def open_paths(self, paths: list[Path]) -> None:
        """
        Add image files, or every image inside directories, to the image list.

        Parameters
        ----------
        paths : list[Path]
            Image files and directories.
        """
        collection: ImageCollection = ImageCollection.gather(paths, self._image_list.image_paths)
        if collection.is_empty:
            self.statusBar().showMessage(collection.describe("No new images found"))
            return
        self._center_stack.setCurrentWidget(self._canvas)
        self._result_panel.add_images(collection.image_paths)
        self._image_list.add_images(collection.image_paths)
        self._images_section.set_title(self._image_list.title)
        self._schedule_review_refresh()
        added_count: int = len(collection.image_paths)
        self.statusBar().showMessage(
            collection.describe(f"Added {added_count} image{'' if added_count == 1 else 's'}"), 5000
        )
        self._save_session()
        self._resume_background_detection()

    def restore_session(self) -> None:
        """
        Open the images that were open when the window last closed, and show the image shown then.

        Image files that no longer exist are skipped and counted in the status bar.
        """
        session: Session = self._session_store.load()
        existing_paths: list[Path] = [image_path for image_path in session.image_paths if image_path.is_file()]
        missing_count: int = len(session.image_paths) - len(existing_paths)
        if not existing_paths:
            if missing_count:
                self.statusBar().showMessage(f"None of the {missing_count} images of the last session exist any more.")
            return
        self.open_paths(existing_paths)
        if session.current_path is not None:
            self._image_list.select(session.current_path)
        restored_count: int = len(existing_paths)
        missing_note: str = f" ({missing_count} missing skipped)" if missing_count else ""
        self.statusBar().showMessage(
            f"Restored {restored_count} image{'' if restored_count == 1 else 's'} of the last session{missing_note}.",
            5000,
        )

    def close_images(self, image_paths: tuple[Path, ...]) -> None:
        """
        Remove images from the image list and the detection table, keeping their stored results.

        Parameters
        ----------
        image_paths : tuple[Path, ...]
            Open images to close; others are ignored.
        """
        closed_paths: tuple[Path, ...] = tuple(path for path in image_paths if path in self._image_list.image_paths)
        if not closed_paths:
            return
        self._result_panel.remove_images(closed_paths)
        self._image_list.remove_images(closed_paths)
        self._images_section.set_title(self._image_list.title)
        if not self._image_list.image_paths:
            self._forget_current_image()
            self._canvas.clear_detections()
            self._center_stack.setCurrentWidget(self._drop_zone)
        self._schedule_review_refresh()
        self._save_session()
        closed_count: int = len(closed_paths)
        self.statusBar().showMessage(
            f"Closed {closed_count} image{'' if closed_count == 1 else 's'}.", self.NOTICE_TIMEOUT_MILLISECONDS
        )

    def save_results(self) -> None:
        """
        Write the stored results to the data directory now, reporting a failure in the status bar.
        """
        self._save_timer.stop()
        try:
            self._result_store.save(self._result_library)
        except OSError as error:
            self.statusBar().showMessage(f"Could not save the results: {error}")

    def closeEvent(self, event: QCloseEvent) -> None:
        self._runner.shutdown()
        self.save_results()
        self._save_session()
        super().closeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        dropped_paths: list[Path] = self._local_paths_of(event.mimeData())
        if not dropped_paths:
            event.ignore()
            return
        collection: ImageCollection = ImageCollection.gather(dropped_paths, self._image_list.image_paths)
        self._is_drop_acceptable = not collection.is_empty
        self._drop_overlay.present(collection, self._splitter.geometry())
        event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if self._is_drop_acceptable:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._drop_overlay.hide()

    def dropEvent(self, event: QDropEvent) -> None:
        self._drop_overlay.hide()
        event.acceptProposedAction()
        self.open_paths(self._local_paths_of(event.mimeData()))

    @staticmethod
    def _local_paths_of(mime_data: QMimeData) -> list[Path]:
        return [Path(url.toLocalFile()) for url in mime_data.urls() if url.isLocalFile()]

    def _build_layout(self) -> CollapsibleSection:
        self._sidebar.add_section("Model", self._settings_panel, is_stretched=False)
        self._sidebar.add_section("Classes", self._class_editor, is_stretched=True)
        images_section: CollapsibleSection = self._sidebar.add_section(
            self._image_list.title, self._image_list, is_stretched=True
        )

        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._center_stack)
        self._result_splitter.addWidget(self._profile_panel)
        self._result_splitter.addWidget(self._result_panel)
        self._result_splitter.setCollapsible(0, False)
        self._result_splitter.setCollapsible(1, False)
        self._result_splitter.setStretchFactor(1, 1)
        self._result_splitter.setSizes([self.DEFAULT_PROFILE_PANEL_HEIGHT, self.DEFAULT_RESULT_PANEL_HEIGHT])
        self._splitter.addWidget(self._result_splitter)
        self._splitter.setCollapsible(self.SIDEBAR_INDEX, False)
        self._splitter.setCollapsible(self.CANVAS_INDEX, False)
        self._splitter.setCollapsible(self.RESULT_INDEX, False)
        self._splitter.setStretchFactor(self.CANVAS_INDEX, 1)
        self._splitter.setSizes([self.DEFAULT_SIDEBAR_WIDTH, 800, 380])
        self.setCentralWidget(self._splitter)
        return images_section

    def _build_toolbar(self) -> None:
        toolbar: QToolBar = self.addToolBar("Main")
        toolbar.setMovable(False)
        open_images_action: QAction = QAction("Open Images…", self)
        open_images_action.setShortcut(QKeySequence.StandardKey.Open)
        open_images_action.triggered.connect(self._choose_images)
        open_folder_action: QAction = QAction("Open Folder…", self)
        open_folder_action.triggered.connect(self._choose_folder)
        toolbar.addAction(open_images_action)
        toolbar.addAction(open_folder_action)
        toolbar.addSeparator()
        self._previous_image_action.setToolTip("Show the previous image (Left or Page Up on the image or the list)")
        self._next_image_action.setToolTip("Show the next image (Right or Page Down on the image or the list)")
        toolbar.addAction(self._previous_image_action)
        toolbar.addAction(self._next_image_action)
        toolbar.addSeparator()
        toolbar.addWidget(self._detect_button)
        toolbar.addWidget(self._detect_all_button)
        toolbar.addSeparator()
        self._export_action.setShortcut(QKeySequence("Ctrl+E"))
        self._export_action.setToolTip(
            "Detect every open image and save the results as annotation files "
            + f"({self._export_action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)})"
        )
        self._export_action.triggered.connect(self._export_detections)
        toolbar.addAction(self._export_action)
        toolbar.addSeparator()
        view_button: QToolButton = QToolButton()
        view_button.setText(DisplayMenu.TITLE)
        view_button.setToolTip("Choose how detection boxes are drawn")
        view_button.setMenu(self._display_menu)
        view_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(view_button)
        statistics_action: QAction = QAction("Statistics…", self)
        statistics_action.setShortcut(QKeySequence("Ctrl+I"))
        statistics_action.setToolTip(
            "Detections per class, confidence histograms, class minimums and model comparison "
            + f"({statistics_action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)})"
        )
        statistics_action.triggered.connect(self._show_statistics_window)
        toolbar.addAction(statistics_action)

        detect_action: QAction = QAction("Detect", self)
        detect_action.setShortcut(QKeySequence("Ctrl+Return"))
        detect_action.triggered.connect(self._request_detection)
        self.addAction(detect_action)
        detect_all_action: QAction = QAction("Detect All", self)
        detect_all_action.setShortcut(QKeySequence("Ctrl+Shift+Return"))
        detect_all_action.triggered.connect(self._detect_all)
        self.addAction(detect_all_action)
        self._detect_all_button.setToolTip(
            "Detect every open image and list the results in the table "
            + f"({detect_all_action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)})"
        )
        for step, keys in (
            (-1, (Qt.Key.Key_Left, Qt.Key.Key_PageUp)),
            (1, (Qt.Key.Key_Right, Qt.Key.Key_PageDown)),
        ):
            for widget in (self._canvas, self._image_list):
                self._add_navigation_shortcut(widget, step, keys)

    def _add_navigation_shortcut(self, widget: QWidget, step: int, keys: tuple[Qt.Key, ...]) -> None:
        action: QAction = QAction(widget)
        action.setShortcuts([QKeySequence(key) for key in keys])
        action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        action.triggered.connect(lambda: self._show_neighbor_image(step))
        widget.addAction(action)

    def _connect_signals(self) -> None:
        self._image_list.current_image_changed.connect(self._on_image_selected)
        self._detect_button.clicked.connect(self._request_detection)
        self._detect_all_button.clicked.connect(self._detect_all)
        self._class_editor.message_posted.connect(self._show_notice)
        self._result_panel.message_posted.connect(self._show_notice)
        self._result_panel.detection_selected.connect(self._on_detection_selected)
        self._result_panel.image_selected.connect(self._on_result_image_selected)
        self._result_panel.selection_cleared.connect(self._on_detection_selection_cleared)
        self._result_panel.clear_requested.connect(self._clear_results)
        self._result_panel.update_outdated_requested.connect(self._update_outdated)
        self._class_editor.classes_changed.connect(self._on_classes_changed)
        self._profile_panel.profile_selected.connect(self._on_profile_selected)
        self._profile_panel.removal_requested.connect(self._remove_profile)
        self._drop_zone.open_images_requested.connect(self._choose_images)
        self._drop_zone.open_folder_requested.connect(self._choose_folder)
        self._settings_panel.backend_changed.connect(self._update_image_prompt_support)
        self._runner.busy_changed.connect(self._on_busy_changed)
        self._runner.status_changed.connect(self.statusBar().showMessage)
        self._runner.succeeded.connect(self._on_detection_succeeded)
        self._runner.failed.connect(self._on_detection_failed)
        self._runner.background_succeeded.connect(self._on_background_detection_succeeded)
        self._runner.background_failed.connect(self._on_background_detection_failed)
        self._runner.batch_image_detected.connect(self._on_batch_image_detected)
        self._runner.batch_finished.connect(self._on_batch_finished)
        self._runner.batch_failed.connect(self._on_batch_failed)
        self._result_panel.listing_changed.connect(self._on_listing_changed)
        self._result_panel.acceptance_changed.connect(self._schedule_save)
        self._image_list.removal_requested.connect(self.close_images)
        self._display_menu.options_changed.connect(self._canvas.set_display_options)
        self._statistics_window.thresholds_changed.connect(self._apply_class_thresholds)
        self._statistics_window.comparison_selected.connect(self._compare_with)
        self._statistics_window.comparison_cleared.connect(lambda: self._compare_with(None))
        self._previous_image_action.triggered.connect(lambda: self._show_neighbor_image(-1))
        self._next_image_action.triggered.connect(lambda: self._show_neighbor_image(1))
        self._save_timer.timeout.connect(self.save_results)
        self._review_refresh_timer.timeout.connect(self._refresh_review)
        self._update_image_prompt_support()
        self._update_navigation()

    def _choose_images(self) -> None:
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Open Images", "", f"Images ({LoadedImage.suffix_patterns()})"
        )
        self.open_paths([Path(file_name) for file_name in file_names])

    def _choose_folder(self) -> None:
        directory: str = QFileDialog.getExistingDirectory(self, "Open Folder")
        if directory:
            self.open_paths([Path(directory)])

    def _on_image_selected(self) -> None:
        self._summary_label.clear()
        path: Path | None = self._image_list.current_path
        if path is None:
            self._forget_current_image()
            return
        try:
            self._current_image = LoadedImage.open(path)
        except OSError as error:
            self._forget_current_image()
            QMessageBox.warning(self, "Cannot open image", f"{path}\n{error}")
            return
        self._canvas.set_image(self._current_image.image)
        self._result_panel.set_current_image(path)
        self._refresh_canvas()
        self._update_navigation()
        width, height = self._current_image.image.size
        self.statusBar().showMessage(f"{path.name} ({width}x{height})")
        self._resume_background_detection()

    def _resume_background_detection(self) -> None:
        self._background_queue.resume()
        self._detect_in_background()

    def _detect_in_background(self) -> None:
        if not self._class_editor.classes:
            return
        if self._runner.is_busy:
            if self._current_image is not None:
                self._runner.prioritize(self._current_image.path)
            return
        settings: DetectorSettings = self._settings_panel.current_settings()
        profile: DetectorProfile = DetectorProfile.of(settings)
        image_path: Path | None = self._background_queue.next_image(
            profile,
            self._shown_profile,
            self._current_signature(),
            None if self._current_image is None else self._current_image.path,
            self._image_list.image_paths,
        )
        if image_path is None:
            return
        labeled_prompt: LabeledPrompt | None = self._build_background_prompt()
        if labeled_prompt is None:
            return
        self._switch_to(profile)
        self._runner.detect_in_background(
            DetectionRequest(settings=settings, image_path=image_path, labeled_prompt=labeled_prompt)
        )

    def _current_signature(self) -> PromptSignature:
        return self._reference_board.signature_of(self._class_editor.classes)

    def _on_classes_changed(self) -> None:
        self._background_queue.forget_failures()
        self._refresh_outdated_marks()
        self._schedule_review_refresh()
        self._resume_background_detection()

    def _refresh_outdated_marks(self) -> None:
        self._refresh_profile_panel()
        if self._shown_profile is None:
            self._result_panel.set_prompt_changes({})
            return
        self._result_panel.set_prompt_changes(
            self._result_library.outdated_images(self._shown_profile, self._current_signature())
        )

    def _shown_catalog(self) -> DetectionCatalog | None:
        shown_profile: DetectorProfile | None = self._shown_profile
        if shown_profile is None or shown_profile not in self._result_library:
            return None
        return self._result_library.catalog_of(shown_profile)

    def _refresh_canvas(self) -> None:
        catalog: DetectionCatalog | None = self._shown_catalog()
        if self._current_image is None or catalog is None:
            self._canvas.clear_detections()
            return
        image_path: Path = self._current_image.path
        stored_result: DetectionResult | None = catalog.result_of(image_path)
        if stored_result is None:
            self._canvas.clear_detections()
            return
        compared_result: DetectionResult | None = None
        if self._compared_profile is not None and self._compared_profile in self._result_library:
            compared_result = self._result_library.catalog_of(self._compared_profile).result_of(image_path)
        self._canvas.show_overlay(
            DetectionOverlay(
                result=stored_result,
                listed_indices=self._result_panel.listed_detection_indices(image_path),
                rejected_indices=catalog.rejected_indices_of(image_path),
                comparison=compared_result,
                comparison_name="" if self._compared_profile is None else self._compared_profile.model_name,
            )
        )

    def _on_listing_changed(self) -> None:
        self._refresh_canvas()
        self._schedule_review_refresh()

    def _schedule_review_refresh(self) -> None:
        self._review_refresh_timer.start()

    def _refresh_review(self) -> None:
        self._refresh_image_statuses()
        if self._statistics_window.isVisible():
            self._refresh_statistics()

    def _refresh_image_statuses(self) -> None:
        catalog: DetectionCatalog | None = self._shown_catalog()
        outdated_paths: frozenset[Path] = frozenset(self._result_panel.outdated_image_paths)
        settings_profile: DetectorProfile = DetectorProfile.of(self._settings_panel.current_settings())
        self._image_list.set_statuses(
            {
                image_path: ImageStatus.of(
                    image_path,
                    catalog,
                    self._class_thresholds,
                    is_outdated=image_path in outdated_paths,
                    is_failed=self._background_queue.is_failed(settings_profile, image_path),
                )
                for image_path in self._image_list.image_paths
            }
        )

    def _show_statistics_window(self) -> None:
        self._refresh_statistics()
        self._statistics_window.show()
        self._statistics_window.raise_()
        self._statistics_window.activateWindow()

    def _refresh_statistics(self) -> None:
        shown_profile: DetectorProfile | None = self._shown_profile
        class_names: tuple[str, ...] = self._class_editor.class_names
        image_paths: tuple[Path, ...] = self._image_list.image_paths
        self._statistics_window.set_comparison_candidates(
            tuple(profile for profile in self._result_library.profiles if profile != shown_profile),
            self._compared_profile,
        )
        shown_catalog: DetectionCatalog | None = self._shown_catalog()
        if shown_profile is None or shown_catalog is None:
            self._statistics_window.show_statistics(None, "", class_names, self._class_thresholds)
            self._statistics_window.show_comparison(None)
            return
        self._statistics_window.show_statistics(
            ResultStatistics.of(shown_catalog, image_paths, class_names, self._class_thresholds),
            f"{shown_profile.model_name} ({shown_profile.options_text})",
            class_names,
            self._class_thresholds,
        )
        compared_profile: DetectorProfile | None = self._compared_profile
        self._statistics_window.show_comparison(
            None
            if compared_profile is None
            else ProfileComparison.between(
                shown_catalog, self._result_library.catalog_of(compared_profile), image_paths, class_names
            )
        )

    def _apply_class_thresholds(self, class_thresholds: ClassThresholds) -> None:
        self._class_thresholds = class_thresholds
        self._result_panel.set_class_thresholds(class_thresholds)
        try:
            self._class_threshold_store.save(class_thresholds)
        except OSError as error:
            self.statusBar().showMessage(f"Could not save the class minimums: {error}")

    def _compare_with(self, profile: DetectorProfile | None) -> None:
        is_comparable: bool = profile is not None and profile in self._result_library and profile != self._shown_profile
        self._compared_profile = profile if is_comparable else None
        self._display_menu.set_comparison_available(self._compared_profile is not None)
        self._refresh_canvas()
        if self._statistics_window.isVisible():
            self._refresh_statistics()

    def _show_neighbor_image(self, step: int) -> None:
        self._image_list.select_neighbor(step)

    def _update_navigation(self) -> None:
        current_row: int = self._image_list.currentRow()
        image_count: int = len(self._image_list.image_paths)
        self._previous_image_action.setEnabled(current_row > 0)
        self._next_image_action.setEnabled(0 <= current_row < image_count - 1)

    def _save_session(self) -> None:
        try:
            self._session_store.save(
                Session(image_paths=self._image_list.image_paths, current_path=self._image_list.current_path)
            )
        except OSError as error:
            self.statusBar().showMessage(f"Could not save the open images: {error}")

    def _schedule_save(self) -> None:
        self._save_timer.start()

    def _load_results(self) -> ResultLibrary:
        try:
            return self._result_store.load()
        except (OSError, ValueError) as error:
            self._restore_notice = f"Could not restore the saved results: {error}"
            return ResultLibrary()

    def _show_restored_results(self) -> None:
        profiles: tuple[DetectorProfile, ...] = self._result_library.profiles
        if not profiles:
            return
        settings_profile: DetectorProfile = DetectorProfile.of(self._settings_panel.current_settings())
        self._display_profile(settings_profile if settings_profile in profiles else profiles[-1])
        self._refresh_profile_panel()

    def _forget_current_image(self) -> None:
        self._current_image = None
        self._result_panel.set_current_image(None)
        self._update_navigation()

    def _is_ready_to_detect(self, missing_image_notice: str | None) -> bool:
        if self._runner.is_busy:
            self.statusBar().showMessage("A detection is already running.")
            return False
        if missing_image_notice is not None:
            self.statusBar().showMessage(missing_image_notice)
            return False
        if not self._class_editor.classes:
            self.statusBar().showMessage("Add at least one class to detect.")
            return False
        return True

    def _request_detection(self) -> None:
        image: LoadedImage | None = self._current_image
        if not self._is_ready_to_detect("Open an image first." if image is None else None) or image is None:
            return
        labeled_prompt: LabeledPrompt | None = self._build_prompt()
        if labeled_prompt is None:
            return
        settings: DetectorSettings = self._settings_panel.current_settings()
        self._switch_to(DetectorProfile.of(settings))
        self._runner.detect(DetectionRequest(settings=settings, image_path=image.path, labeled_prompt=labeled_prompt))

    def _on_detection_succeeded(self, outcome: DetectionOutcome) -> None:
        self._record_outcome(outcome)
        self.statusBar().showMessage("Done.", 3000)

    def _on_background_detection_succeeded(self, outcome: DetectionOutcome) -> None:
        self._record_outcome(outcome)
        self.statusBar().clearMessage()
        self._detect_in_background()

    def _on_background_detection_failed(self, request: DetectionRequest, failure: DetectionFailure) -> None:
        self._background_queue.record_failure(request, failure)
        match failure.kind:
            case DetectionFailureKind.UNREADABLE_IMAGE:
                self._detect_in_background()
            case DetectionFailureKind.DETECTION_ERROR:
                self.statusBar().showMessage(
                    f"Background detection of {request.image_path.name} failed: {failure.message}"
                )

    def _record_outcome(self, outcome: DetectionOutcome) -> None:
        self._record_result(
            DetectorProfile.of(outcome.request.settings),
            outcome.request.image_path,
            outcome.result,
            outcome.request.labeled_prompt,
        )
        if self._current_image is None or self._current_image.path != outcome.request.image_path:
            return
        load_note: str = " (model loaded)" if outcome.is_model_reloaded else ""
        prompt_kinds: str = "+".join(sorted(kind.value for kind in outcome.result.prompt.kinds))
        self._summary_label.setText(
            f"{outcome.request.settings.backend.value} | {outcome.request.settings.weights_path} | "
            + f"{len(outcome.result.prompt.queries)} {prompt_kinds} prompts | "
            + f"{len(outcome.result)} detections | {outcome.inference_seconds * 1000:.0f} ms{load_note}"
        )

    def _on_detection_failed(self, failure: DetectionFailure) -> None:
        self.statusBar().showMessage("Detection failed.")
        QMessageBox.critical(self, "Detection failed", failure.message)

    def _build_prompt(self) -> LabeledPrompt | None:
        supported_kinds: frozenset[PromptKind] = self._settings_panel.selected_backend.supported_prompt_kinds
        definitions: tuple[ClassDefinition, ...] = self._class_editor.classes
        skipped_names: tuple[str, ...] = self._reference_board.reference_only_classes(definitions, supported_kinds)
        if skipped_names and len(skipped_names) < len(definitions):
            if not self._confirm_skipping(skipped_names):
                return None
            definitions = tuple(definition for definition in definitions if definition.name not in skipped_names)
        issue: str | None = self._reference_board.prompt_issue(definitions, supported_kinds)
        if issue is not None:
            QMessageBox.warning(self, "Invalid input", issue)
            return None
        return self._reference_board.build_prompt(definitions, supported_kinds)

    def _build_background_prompt(self) -> LabeledPrompt | None:
        supported_kinds: frozenset[PromptKind] = self._settings_panel.selected_backend.supported_prompt_kinds
        definitions: tuple[ClassDefinition, ...] = self._class_editor.classes
        skipped_names: tuple[str, ...] = self._reference_board.reference_only_classes(definitions, supported_kinds)
        if skipped_names and frozenset(skipped_names) != self._approved_skipped_classes:
            return None
        kept_definitions: tuple[ClassDefinition, ...] = tuple(
            definition for definition in definitions if definition.name not in skipped_names
        )
        if self._reference_board.prompt_issue(kept_definitions, supported_kinds) is not None:
            return None
        return self._reference_board.build_prompt(kept_definitions, supported_kinds)

    def _confirm_skipping(self, skipped_names: tuple[str, ...]) -> bool:
        if frozenset(skipped_names) == self._approved_skipped_classes:
            return True
        listed_names: str = "\n".join(f"  • {name}" for name in skipped_names)
        answer: QMessageBox.StandardButton = QMessageBox.question(
            self,
            "Skip reference-only classes?",
            f"{self._settings_panel.selected_backend.value} does not take reference images, "
            + f"so these classes have no usable query:\n{listed_names}\n\n"
            + "Detect the other classes without them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        is_approved: bool = answer == QMessageBox.StandardButton.Yes
        if is_approved:
            self._approved_skipped_classes = frozenset(skipped_names)
        return is_approved

    def _record_result(
        self, profile: DetectorProfile, image_path: Path, result: DetectionResult, labeled_prompt: LabeledPrompt
    ) -> None:
        records: tuple[DetectionRecord, ...] = self._result_library.record(profile, image_path, result, labeled_prompt)
        self._schedule_save()
        if profile != self._shown_profile or image_path not in self._image_list.image_paths:
            self._refresh_profile_panel()
            if profile == self._compared_profile:
                self._refresh_canvas()
            return
        self._result_panel.replace_image(image_path, records)
        self._refresh_outdated_marks()

    def _switch_to(self, profile: DetectorProfile) -> None:
        self._background_queue.unpin()
        self._result_library.add(profile)
        if profile != self._shown_profile:
            self._display_profile(profile)
        self._refresh_profile_panel()

    def _on_profile_selected(self, profile: DetectorProfile) -> None:
        self._background_queue.pin()
        self._display_profile(profile)
        self._resume_background_detection()

    def _display_profile(self, profile: DetectorProfile | None) -> None:
        self._shown_profile = profile
        if self._compared_profile == profile:
            self._compare_with(None)
        catalog: DetectionCatalog | None = None if profile is None else self._result_library.catalog_of(profile)
        self._result_panel.show_catalog(catalog)
        self._refresh_outdated_marks()
        self._refresh_canvas()
        self._schedule_review_refresh()
        self._summary_label.clear()

    def _remove_profile(self, profile: DetectorProfile) -> None:
        self._result_library.remove(profile)
        self._schedule_save()
        if profile == self._compared_profile:
            self._compare_with(None)
        if profile == self._shown_profile:
            remaining_profiles: tuple[DetectorProfile, ...] = self._result_library.profiles
            self._display_profile(remaining_profiles[-1] if remaining_profiles else None)
            return
        self._refresh_profile_panel()

    def _refresh_profile_panel(self) -> None:
        self._profile_panel.set_summaries(
            self._result_library.summaries(self._current_signature()), self._shown_profile
        )
        self._schedule_review_refresh()

    def _clear_results(self) -> None:
        self._result_library.clear()
        self._display_profile(None)
        self._compare_with(None)
        self._schedule_save()

    def _detect_all(self) -> None:
        if not self._is_ready_to_detect(self._missing_images_notice()):
            return
        request: BatchDetectionRequest | None = self._build_batch_request(self._image_list.image_paths)
        if request is None:
            return
        self._switch_to(DetectorProfile.of(request.settings))
        self._runner.detect_batch(BatchJob.detect_all(request))

    def _update_outdated(self) -> None:
        outdated_paths: tuple[Path, ...] = self._result_panel.outdated_image_paths
        if not self._is_ready_to_detect(None if outdated_paths else "No outdated images to update."):
            return
        shown_profile: DetectorProfile | None = self._shown_profile
        if shown_profile is not None and not self._is_selected_in_settings(shown_profile):
            self.statusBar().showMessage(
                f"The outdated images were detected with {shown_profile.model_name} "
                + f"({shown_profile.options_text}); choose these model settings to update them."
            )
            return
        request: BatchDetectionRequest | None = self._build_batch_request(outdated_paths)
        if request is None:
            return
        self._switch_to(DetectorProfile.of(request.settings))
        self._runner.detect_batch(BatchJob.detect_all(request))

    def _is_selected_in_settings(self, profile: DetectorProfile) -> bool:
        return DetectorProfile.of(self._settings_panel.current_settings()) == profile

    def _export_detections(self) -> None:
        image_paths: tuple[Path, ...] = self._image_list.image_paths
        missing_images_notice: str | None = self._missing_images_notice()
        if missing_images_notice is not None:
            self.statusBar().showMessage(missing_images_notice)
            return
        if self._runner.is_busy:
            self.statusBar().showMessage("A detection is already running.")
            return
        profile: DetectorProfile = self._shown_profile or DetectorProfile.of(self._settings_panel.current_settings())
        signature: PromptSignature = self._current_signature()
        pending_paths: tuple[Path, ...] = tuple(
            image_path
            for image_path in image_paths
            if not self._is_up_to_date(self._result_library.prompt_change_of(profile, image_path, signature))
        )
        if pending_paths and not self._is_selected_in_settings(profile):
            self.statusBar().showMessage(
                f"{len(pending_paths)} images have no up-to-date result of {profile.model_name} "
                + f"({profile.options_text}); choose these model settings to detect them before exporting."
            )
            return
        options: ExportOptions | None = self._export_dialog.ask(
            profile.model_name, len(image_paths), len(pending_paths)
        )
        if options is None:
            return
        if not pending_paths:
            self._write_export(profile, options, "")
            return
        if not self._is_ready_to_detect(None):
            return
        request: BatchDetectionRequest | None = self._build_batch_request(pending_paths)
        if request is None:
            return
        self._switch_to(profile)
        self._runner.detect_batch(BatchJob.export(request, options))

    @staticmethod
    def _is_up_to_date(change: PromptChange | None) -> bool:
        return change is not None and change.is_unchanged

    def _missing_images_notice(self) -> str | None:
        return None if self._image_list.image_paths else "Open images first."

    def _build_batch_request(self, image_paths: tuple[Path, ...]) -> BatchDetectionRequest | None:
        labeled_prompt: LabeledPrompt | None = self._build_prompt()
        if labeled_prompt is None:
            return None
        return BatchDetectionRequest(
            settings=self._settings_panel.current_settings(), labeled_prompt=labeled_prompt, image_paths=image_paths
        )

    def _on_batch_image_detected(self, job: BatchJob, image_path: Path, result: DetectionResult) -> None:
        self._record_result(DetectorProfile.of(job.request.settings), image_path, result, job.request.labeled_prompt)

    def _on_batch_finished(self, job: BatchJob, summary: BatchDetectionSummary) -> None:
        skipped_note: str = (
            f" ({len(summary.unreadable_paths)} unreadable images skipped)" if summary.unreadable_paths else ""
        )
        match job.purpose:
            case BatchPurpose.DETECT_ALL:
                outcome_text: str = (
                    f"Detect All stopped after {summary.detected_count} images"
                    if summary.is_cancelled
                    else f"Detected {summary.detected_count} images"
                )
                self.statusBar().showMessage(
                    f"{outcome_text}{skipped_note}; {len(self._result_panel.visible_records)} detections listed.",
                    8000,
                )
            case BatchPurpose.EXPORT:
                if summary.is_cancelled:
                    self.statusBar().showMessage(f"Export cancelled after {summary.detected_count} images.", 5000)
                elif job.export_options is not None:
                    self._write_export(DetectorProfile.of(job.request.settings), job.export_options, skipped_note)

    def _write_export(self, profile: DetectorProfile, options: ExportOptions, skipped_note: str) -> None:
        catalog: DetectionCatalog = self._result_library.add(profile)
        selection: ExportSelection = ExportSelection(
            class_thresholds=self._class_thresholds,
            minimum_confidence=options.minimum_confidence,
            listed_indices=(
                self._result_panel.listed_detection_indices_by_image()
                if options.scope == ExportScope.LISTED and profile == self._shown_profile
                else None
            ),
        )
        archive: DetectionArchive = DetectionArchive()
        selected_results: dict[Path, DetectionResult] = {}
        detection_count: int = 0
        for image_path in self._image_list.image_paths:
            selected_result: DetectionResult | None = selection.selected_result(catalog, image_path)
            if selected_result is not None:
                archive.record(image_path, selected_result)
                selected_results[image_path] = selected_result
                detection_count += len(selected_result)
        try:
            written_paths: tuple[Path, ...] = archive.write(options, self._class_editor.class_names)
        except (ValueError, OSError) as error:
            QMessageBox.critical(self, "Export failed", str(error))
            return
        image_note: str = ""
        if options.is_annotated_image_saved:
            saved_count: int | None = self._save_annotated_images(selected_results, options)
            if saved_count is None:
                return
            image_note = f", {saved_count} images with boxes"
        self.statusBar().showMessage(
            f"Exported {options.annotation_format.display_name}: {len(archive)} images, {detection_count} detections, "
            + f"{len(written_paths)} files{image_note} to {options.output_directory}{skipped_note}.",
            8000,
        )

    def _save_annotated_images(
        self, selected_results: dict[Path, DetectionResult], options: ExportOptions
    ) -> int | None:
        writer: AnnotatedImageWriter = AnnotatedImageWriter(
            ClassPalette.HEX_COLORS, self._canvas.display_options.is_confidence_shown, options.annotated_image_directory
        )
        progress: QProgressDialog = QProgressDialog(
            "Saving images with boxes…", "Cancel", 0, len(selected_results), self
        )
        progress.setWindowTitle(self._export_dialog.WINDOW_TITLE)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(500)
        saved_count: int = 0
        for image_path, selected_result in selected_results.items():
            if progress.wasCanceled():
                break
            progress.setLabelText(f"Saving {image_path.name} with boxes…")
            try:
                writer.write(LoadedImage.open(image_path), selected_result)
            except (ValueError, OSError) as error:
                progress.close()
                QMessageBox.critical(self, "Export failed", f"Could not save {image_path.name} with boxes:\n{error}")
                return None
            saved_count += 1
            progress.setValue(saved_count)
            QApplication.processEvents()
        progress.close()
        return saved_count

    def _on_batch_failed(self, job: BatchJob, message: str) -> None:
        title: str = f"{job.purpose.title} failed"
        self.statusBar().showMessage(f"{title}.")
        QMessageBox.critical(self, title, message)

    def _update_image_prompt_support(self) -> None:
        self._class_editor.set_image_prompt_supported(
            PromptKind.VISUAL in self._settings_panel.selected_backend.supported_prompt_kinds
        )

    def _show_notice(self, message: str) -> None:
        self.statusBar().showMessage(message, self.NOTICE_TIMEOUT_MILLISECONDS)

    def _on_detection_selected(self, record: DetectionRecord) -> None:
        is_other_image: bool = self._current_image is None or self._current_image.path != record.image_path
        if is_other_image and not self._image_list.select(record.image_path):
            return
        if self._current_image is not None and self._current_image.path == record.image_path:
            self._canvas.highlight(record.detection_index)

    def _on_result_image_selected(self, image_path: Path) -> None:
        self._image_list.select(image_path)
        self._canvas.highlight(None)

    def _on_detection_selection_cleared(self) -> None:
        self._canvas.highlight(None)

    def _on_busy_changed(self, is_busy: bool) -> None:
        self._detect_button.setEnabled(not is_busy)
        self._detect_all_button.setEnabled(not is_busy)
        self._export_action.setEnabled(not is_busy)
        self._settings_panel.setEnabled(not is_busy)
        if not is_busy:
            self._resume_background_detection()
