from pathlib import Path

from open_vocabulary_detector import DetectionResult, DetectorSettings, PromptKind
from PySide6.QtCore import QMimeData, Qt
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
    QCheckBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QToolBar,
)

from ..detection import (
    BatchDetectionRequest,
    BatchDetectionSummary,
    DetectionCatalog,
    DetectionOutcome,
    DetectionRecord,
    DetectionRequest,
    LabeledPrompt,
    ReferenceBoard,
)
from ..export import DetectionArchive, ExportOptions
from ..media import ImageCollection, LoadedImage
from ..preset import PresetCatalog
from ..vocabulary import ClassDefinition, ClassListStore
from .class_palette import ClassPalette
from .execution import BatchJob, BatchProgressDialog, BatchPurpose, DetectionRunner
from .export_dialog import ExportDialog
from .intake import DropOverlay, DropZone
from .prompt import ClassEditor
from .sidebar import CollapsibleSection, ImageListPanel, SectionStack, SettingsPanel
from .table import ResultPanel, ResultScope
from .viewer import ImageCanvas


class MainWindow(QMainWindow):
    """
    Main window: class editor, model settings and image list on the left, image with detections in the center,
    detection table on the right.

    The latest result of every detected image is kept, so switching images shows its boxes again without detecting,
    and the detection table can list, filter and sort the detections of every image at once. Detect All detects
    every open image on the worker thread; selecting a detection of another image in the table opens that image.

    Every class is queried by its phrases and, with a backend that takes image prompts (OWL-ViT, YOLOE), by its
    reference images. Detections are reported under the class and name the query that matched.

    Images and folders can be dropped anywhere on the window; while dragging, an overlay previews what the drop
    adds. Until an image is open, the center shows a drop zone instead of the image.

    Export detects every open image with the current model and classes on the worker thread, then writes the
    results in the chosen annotation format. Detect All and export batches can be cancelled from their progress
    dialog.
    """

    WINDOW_TITLE = "OVD GUI"
    DEFAULT_CLASS_NAMES: tuple[str, ...] = ("person", "car", "dog")
    DEFAULT_SIDEBAR_WIDTH = 320
    SIDEBAR_INDEX = 0
    CANVAS_INDEX = 1
    RESULT_INDEX = 2
    NOTICE_TIMEOUT_MILLISECONDS = 3000

    def __init__(self, catalog: PresetCatalog, class_list_store: ClassListStore) -> None:
        """
        Parameters
        ----------
        catalog : PresetCatalog
            Presets offered in the model settings.
        class_list_store : ClassListStore
            Data directory remembering the class list between runs and holding saved class lists.
        """
        super().__init__()
        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(1400, 850)
        self.setAcceptDrops(True)

        self._current_image: LoadedImage | None = None
        self._detection_catalog: DetectionCatalog = DetectionCatalog()
        self._detection_archive: DetectionArchive = DetectionArchive()
        self._reference_board: ReferenceBoard = ReferenceBoard()

        palette: ClassPalette = ClassPalette()
        self._settings_panel: SettingsPanel = SettingsPanel(catalog)
        self._image_list: ImageListPanel = ImageListPanel()
        self._canvas: ImageCanvas = ImageCanvas(palette)
        self._canvas.setAcceptDrops(False)
        self._drop_zone: DropZone = DropZone()
        self._center_stack: QStackedWidget = QStackedWidget()
        self._center_stack.addWidget(self._drop_zone)
        self._center_stack.addWidget(self._canvas)
        self._result_panel: ResultPanel = ResultPanel(palette)
        self._class_editor: ClassEditor = ClassEditor(palette, class_list_store, self._reference_board)
        self._class_editor.restore(tuple(ClassDefinition.named(name) for name in self.DEFAULT_CLASS_NAMES))
        self._detect_button: QPushButton = QPushButton("Detect")
        self._detect_all_button: QPushButton = QPushButton("Detect All")
        self._auto_detect_check: QCheckBox = QCheckBox("Auto detect on image change")
        self._auto_detect_check.setToolTip("Detect an image when it is shown and has no result yet")
        self._progress_bar: QProgressBar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setMaximumWidth(160)
        self._progress_bar.setVisible(False)
        self._summary_label: QLabel = QLabel()
        self._export_dialog: ExportDialog = ExportDialog(self)
        self._export_action: QAction = QAction("Export...", self)

        self._runner: DetectionRunner = DetectionRunner(self)
        self._batch_progress_dialog: BatchProgressDialog = BatchProgressDialog(self._runner, self)

        self._splitter: QSplitter = QSplitter(Qt.Orientation.Horizontal)
        self._sidebar: SectionStack = SectionStack()
        self._images_section: CollapsibleSection = self._build_layout()
        self._drop_overlay: DropOverlay = DropOverlay(self)
        self._is_drop_acceptable: bool = False
        self._build_toolbar()
        self._connect_signals()

        self.statusBar().addPermanentWidget(self._summary_label)
        self.statusBar().addPermanentWidget(self._progress_bar)
        self.statusBar().showMessage("Drop images or folders to start.")

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
        self._image_list.add_images(collection.image_paths)
        self._images_section.set_title(self._image_list.title)
        added_count: int = len(collection.image_paths)
        self.statusBar().showMessage(
            collection.describe(f"Added {added_count} image{'' if added_count == 1 else 's'}"), 5000
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self._runner.shutdown()
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
        self._sidebar.add_section("Classes", self._class_editor, is_stretched=True)
        self._sidebar.add_section("Model", self._settings_panel, is_stretched=False)
        images_section: CollapsibleSection = self._sidebar.add_section(
            self._image_list.title, self._image_list, is_stretched=True
        )

        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._center_stack)
        self._splitter.addWidget(self._result_panel)
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
        open_images_action: QAction = QAction("Open Images...", self)
        open_images_action.setShortcut(QKeySequence.StandardKey.Open)
        open_images_action.triggered.connect(self._choose_images)
        open_folder_action: QAction = QAction("Open Folder...", self)
        open_folder_action.triggered.connect(self._choose_folder)
        toolbar.addAction(open_images_action)
        toolbar.addAction(open_folder_action)
        toolbar.addSeparator()
        toolbar.addWidget(self._detect_button)
        toolbar.addWidget(self._detect_all_button)
        toolbar.addWidget(self._auto_detect_check)
        toolbar.addSeparator()
        self._export_action.setShortcut(QKeySequence("Ctrl+E"))
        self._export_action.setToolTip(
            "Detect every open image and save the results as annotation files "
            + f"({self._export_action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)})"
        )
        self._export_action.triggered.connect(self._export_detections)
        toolbar.addAction(self._export_action)

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

    def _connect_signals(self) -> None:
        self._image_list.current_image_changed.connect(self._on_image_selected)
        self._detect_button.clicked.connect(self._request_detection)
        self._detect_all_button.clicked.connect(self._detect_all)
        self._class_editor.detection_requested.connect(self._request_detection)
        self._class_editor.message_posted.connect(self._show_notice)
        self._result_panel.detection_selected.connect(self._on_detection_selected)
        self._result_panel.selection_cleared.connect(self._on_detection_selection_cleared)
        self._result_panel.clear_requested.connect(self._clear_results)
        self._drop_zone.open_images_requested.connect(self._choose_images)
        self._drop_zone.open_folder_requested.connect(self._choose_folder)
        self._settings_panel.backend_changed.connect(self._update_image_prompt_support)
        self._runner.busy_changed.connect(self._on_busy_changed)
        self._runner.status_changed.connect(self.statusBar().showMessage)
        self._runner.succeeded.connect(self._on_detection_succeeded)
        self._runner.failed.connect(self._on_detection_failed)
        self._runner.batch_image_detected.connect(self._on_batch_image_detected)
        self._runner.batch_finished.connect(self._on_batch_finished)
        self._runner.batch_failed.connect(self._on_batch_failed)
        self._update_image_prompt_support()

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
        stored_result: DetectionResult | None = self._detection_catalog.result_of(path)
        if stored_result is not None:
            self._canvas.show_result(stored_result)
        width, height = self._current_image.image.size
        self.statusBar().showMessage(f"{path.name} ({width}x{height})")
        if self._auto_detect_check.isChecked() and stored_result is None:
            self._request_detection()

    def _forget_current_image(self) -> None:
        self._current_image = None
        self._result_panel.set_current_image(None)

    def _is_ready_to_detect(self, missing_image_notice: str | None) -> bool:
        if self._runner.is_busy:
            self.statusBar().showMessage("A detection is already running.")
            return False
        if missing_image_notice is not None:
            self.statusBar().showMessage(missing_image_notice)
            return False
        self._class_editor.commit_pending_text()
        if not self._class_editor.classes:
            self.statusBar().showMessage("Add at least one class to detect.")
            return False
        return True

    def _request_detection(self) -> None:
        image: LoadedImage | None = self._current_image
        if not self._is_ready_to_detect("Open an image first." if image is None else None) or image is None:
            return
        try:
            settings: DetectorSettings = self._settings_panel.current_settings()
            labeled_prompt: LabeledPrompt = self._build_prompt()
        except ValueError as error:
            QMessageBox.warning(self, "Invalid input", str(error))
            return
        self._runner.detect(DetectionRequest(settings=settings, image=image.image, labeled_prompt=labeled_prompt))

    def _on_detection_succeeded(self, outcome: DetectionOutcome) -> None:
        if self._current_image is None or outcome.request.image is not self._current_image.image:
            self.statusBar().showMessage("Image changed during detection; result discarded.")
            return
        self._record_result(self._current_image.path, outcome.result, outcome.request.labeled_prompt.query_labels)
        load_note: str = " (model loaded)" if outcome.is_model_reloaded else ""
        prompt_kinds: str = "+".join(sorted(kind.value for kind in outcome.result.prompt.kinds))
        self._summary_label.setText(
            f"{outcome.request.settings.backend.value} | {outcome.request.settings.weights_path} | "
            + f"{len(outcome.result.prompt.queries)} {prompt_kinds} queries | "
            + f"{len(outcome.result)} detections | {outcome.inference_seconds * 1000:.0f} ms{load_note}"
        )
        self.statusBar().showMessage("Done.", 3000)

    def _on_detection_failed(self, message: str) -> None:
        self.statusBar().showMessage("Detection failed.")
        QMessageBox.critical(self, "Detection failed", message)

    def _build_prompt(self) -> LabeledPrompt:
        return self._reference_board.build_prompt(
            self._class_editor.classes, self._settings_panel.selected_backend.supported_prompt_kinds
        )

    def _record_result(self, image_path: Path, result: DetectionResult, query_labels: tuple[str, ...]) -> None:
        records: tuple[DetectionRecord, ...] = self._detection_catalog.record(image_path, result, query_labels)
        self._result_panel.replace_image(image_path, records)
        if self._current_image is not None and self._current_image.path == image_path:
            self._canvas.show_result(result)

    def _clear_results(self) -> None:
        self._detection_catalog.clear()
        self._result_panel.clear()
        self._canvas.clear_detections()
        self._summary_label.clear()

    def _detect_all(self) -> None:
        if not self._is_ready_to_detect(self._missing_images_notice()):
            return
        request: BatchDetectionRequest | None = self._build_batch_request()
        if request is None:
            return
        self._result_panel.set_scope(ResultScope.ALL_IMAGES)
        self._runner.detect_batch(BatchJob.detect_all(request))

    def _export_detections(self) -> None:
        if not self._is_ready_to_detect(self._missing_images_notice()):
            return
        options: ExportOptions | None = self._export_dialog.ask(len(self._image_list.image_paths))
        if options is None:
            return
        request: BatchDetectionRequest | None = self._build_batch_request()
        if request is None:
            return
        self._detection_archive.clear()
        self._runner.detect_batch(BatchJob.export(request, options))

    def _missing_images_notice(self) -> str | None:
        return None if self._image_list.image_paths else "Open images first."

    def _build_batch_request(self) -> BatchDetectionRequest | None:
        try:
            return BatchDetectionRequest(
                settings=self._settings_panel.current_settings(),
                labeled_prompt=self._build_prompt(),
                image_paths=self._image_list.image_paths,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Invalid input", str(error))
            return None

    def _on_batch_image_detected(self, job: BatchJob, image_path: Path, result: DetectionResult) -> None:
        self._record_result(image_path, result, job.request.labeled_prompt.query_labels)
        match job.purpose:
            case BatchPurpose.DETECT_ALL:
                return
            case BatchPurpose.EXPORT:
                self._detection_archive.record(image_path, result)

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
                    self._write_export(job.export_options, summary, skipped_note)

    def _write_export(self, options: ExportOptions, summary: BatchDetectionSummary, skipped_note: str) -> None:
        try:
            written_paths: tuple[Path, ...] = self._detection_archive.write(options, self._class_editor.class_names)
        except (ValueError, OSError) as error:
            QMessageBox.critical(self, "Export failed", str(error))
            return
        self.statusBar().showMessage(
            f"Exported {options.annotation_format.display_name}: {summary.detected_count} images, "
            + f"{len(written_paths)} files to {options.output_directory}{skipped_note}.",
            8000,
        )

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

    def _on_detection_selection_cleared(self) -> None:
        self._canvas.highlight(None)

    def _on_busy_changed(self, is_busy: bool) -> None:
        self._detect_button.setEnabled(not is_busy)
        self._detect_all_button.setEnabled(not is_busy)
        self._export_action.setEnabled(not is_busy)
        self._settings_panel.setEnabled(not is_busy)
        self._progress_bar.setVisible(is_busy)
