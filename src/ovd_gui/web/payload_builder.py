from pathlib import Path

from object_detection_format import AnnotationFormat
from open_vocabulary_detector import DetectionResult, Device, PromptKind

from ..analysis import ClassComparison, ClassStatistics, ConfidenceHistogram, ProfileComparison, ResultStatistics
from ..detection import DetectionCatalog, DetectionRecord, DetectorProfile, PromptChange, ReferenceBoard
from ..export import ExportOptions, ExportScope
from ..media import ClassColors
from ..storage import ClassSet, ClassSetEntry
from ..workspace import (
    ActionReply,
    ClassWorkbench,
    ExportPlan,
    ExportReport,
    ImageStatus,
    ModelSelection,
    ModelSelector,
    RunProgress,
    Workspace,
)
from .image_info import ImageInfo
from .image_preview_cache import ImagePreviewCache
from .json_value import JsonObject, JsonValue
from .profile_key import ProfileKey


class PayloadBuilder:
    """
    JSON documents describing the workspace to the browser.

    Paths are sent as absolute strings and identify open images in every request. Boxes are ``[x1, y1, x2, y2]`` in
    pixels of the EXIF-upright image.
    """

    def __init__(self, preview_cache: ImagePreviewCache) -> None:
        """
        Parameters
        ----------
        preview_cache : ImagePreviewCache
            Reads the version and size of the shown image.
        """
        self._preview_cache: ImagePreviewCache = preview_cache

    def state(self, workspace: Workspace) -> JsonObject:
        """
        Everything shown outside the detection table.

        Parameters
        ----------
        workspace : Workspace
            Workspace to describe.

        Returns
        -------
        JsonObject
            Images with their status, the shown image, model settings, stored profiles, classes, class minimums,
            status, progress and the latest export.
        """
        statuses: dict[Path, ImageStatus] = workspace.image_statuses()
        images: list[JsonValue] = [self._image(image_path, status) for image_path, status in statuses.items()]
        profiles: list[JsonValue] = [
            self._profile(summary.profile, summary.image_count, summary.outdated_image_count, summary.detection_count)
            for summary in workspace.result_library.summaries(workspace.current_signature())
        ]
        background_image_path: Path | None = workspace.background_image_path
        palette: list[JsonValue] = list(ClassColors.HEX_COLORS)
        return {
            "images": images,
            "current_image": self._current_image(workspace),
            "background_image_path": None if background_image_path is None else str(background_image_path),
            "model": self._model(workspace.model_selector, workspace.selection),
            "profiles": profiles,
            "shown_profile_key": self._key_or_none(workspace.shown_profile),
            "compared_profile_key": self._key_or_none(workspace.compared_profile),
            "classes": self._classes(workspace.workbench),
            "class_set": self._class_set_state(workspace.workbench),
            "is_image_prompt_supported": workspace.is_image_prompt_supported,
            "thresholds": self._thresholds(workspace),
            "status": {"message": workspace.status_message, "serial": workspace.status_serial},
            "activity": workspace.activity_message,
            "summary": workspace.summary,
            "progress": self._progress(workspace.progress),
            "is_busy": workspace.is_busy,
            "last_export": self._export_report(workspace.last_export),
            "palette": palette,
            "upload_directory": str(workspace.stores.upload_store.directory),
        }

    def detections(self, workspace: Workspace) -> JsonObject:
        """
        Every open image with the detections of the shown profile.

        Parameters
        ----------
        workspace : Workspace
            Workspace to describe.

        Returns
        -------
        JsonObject
            Profile key and, per open image, whether it was detected, how the classes changed since, and its
            detections.
        """
        catalog: DetectionCatalog | None = workspace.shown_catalog()
        outdated_changes: dict[Path, PromptChange] = workspace.outdated_changes()
        images: list[JsonValue] = []
        for image_path in workspace.image_paths:
            change: PromptChange | None = outdated_changes.get(image_path)
            detections: list[JsonValue] = (
                []
                if catalog is None
                else [self._detection(record, catalog) for record in catalog.records_of(image_path)]
            )
            images.append(
                {
                    "path": str(image_path),
                    "name": image_path.name,
                    "is_detected": catalog is not None and image_path in catalog,
                    "outdated": None if change is None else change.description,
                    "detections": detections,
                }
            )
        return {"profile_key": self._key_or_none(workspace.shown_profile), "images": images}

    def statistics(self, workspace: Workspace) -> JsonObject:
        """
        Per-class statistics of the shown results and the comparison with the compared profile.

        Parameters
        ----------
        workspace : Workspace
            Workspace to describe.

        Returns
        -------
        JsonObject
            Model name, image counts, classes with counts, confidences summary and histogram, the histogram of every
            class, and the comparison.
        """
        statistics: ResultStatistics | None = workspace.statistics()
        shown_profile: DetectorProfile | None = workspace.shown_profile
        comparison: ProfileComparison | None = workspace.comparison()
        return {
            "model": None if shown_profile is None else f"{shown_profile.model_name} ({shown_profile.options_text})",
            "statistics": None if statistics is None else self._result_statistics(statistics),
            "comparison": None if comparison is None else self._comparison(comparison),
        }

    def class_set_entries(self, entries: tuple[ClassSetEntry, ...]) -> JsonObject:
        """
        Saved class sets.

        Parameters
        ----------
        entries : tuple[ClassSetEntry, ...]
            Listed sets.

        Returns
        -------
        JsonObject
            Name, save time, class names and counts of every set; counts are ``None`` for unreadable sets.
        """
        listed: list[JsonValue] = []
        for entry in entries:
            class_names: list[JsonValue] = [] if entry.summary is None else list(entry.summary.class_names)
            listed.append(
                {
                    "name": entry.name,
                    "saved_at": entry.saved_at.isoformat(timespec="seconds"),
                    "is_readable": entry.is_readable,
                    "class_names": class_names,
                    "description": "" if entry.summary is None else entry.summary.description,
                }
            )
        return {"entries": listed}

    def class_set_preview(self, name: str, class_set: ClassSet) -> JsonObject:
        """
        Classes, phrases and image prompts of one saved class set.

        Parameters
        ----------
        name : str
            Set name.
        class_set : ClassSet
            Content of the set.

        Returns
        -------
        JsonObject
            Name and classes with their phrases and reference images with boxes.
        """
        board: ReferenceBoard = ReferenceBoard()
        board.replace(class_set.reference_boxes, class_set.reference_pixels)
        classes: list[JsonValue] = [
            self._class(index, definition.name, definition.text_queries, board)
            for index, definition in enumerate(class_set.classes)
        ]
        return {"name": name, "classes": classes}

    def export_plan(self, plan: ExportPlan, default_directory: Path) -> JsonObject:
        """
        What an export would write, with the choices of the export dialog.

        Parameters
        ----------
        plan : ExportPlan
            Model and image counts.
        default_directory : Path
            Output directory suggested to the user.

        Returns
        -------
        JsonObject
            Model, counts, issue, formats and scopes.
        """
        formats: list[JsonValue] = [
            {
                "value": annotation_format.value,
                "label": annotation_format.display_name,
                "is_confidence_supported": ExportOptions.is_confidence_supported(annotation_format),
            }
            for annotation_format in AnnotationFormat
        ]
        scopes: list[JsonValue] = [
            {"value": scope.value, "label": scope.label, "description": scope.description} for scope in ExportScope
        ]
        return {
            "model_name": plan.profile.model_name,
            "options_text": plan.profile.options_text,
            "image_count": plan.image_count,
            "pending_count": plan.pending_count,
            "issue": plan.issue,
            "formats": formats,
            "scopes": scopes,
            "default_directory": str(default_directory),
        }

    @staticmethod
    def reply(reply: ActionReply) -> JsonObject:
        """
        Answer to a request.

        Parameters
        ----------
        reply : ActionReply
            Answer of the workspace.

        Returns
        -------
        JsonObject
            Status, message and the classes to approve skipping.
        """
        skipped: list[JsonValue] = list(reply.skipped_class_names)
        return {"status": reply.status.value, "message": reply.message, "skipped_class_names": skipped}

    def _image(self, image_path: Path, status: ImageStatus) -> JsonObject:
        return {
            "path": str(image_path),
            "name": image_path.name,
            "state": status.state.value,
            "color": status.state.color,
            "is_marked_filled": status.state.is_marked_filled,
            "count_text": status.count_text,
            "description": status.description,
        }

    def _current_image(self, workspace: Workspace) -> JsonValue:
        image_path: Path | None = workspace.current_path
        if image_path is None:
            return None
        try:
            info: ImageInfo | None = self._preview_cache.info_of(image_path)
        except OSError:
            info = None
        compared: DetectionCatalog | None = workspace.compared_catalog()
        compared_result: DetectionResult | None = None if compared is None else compared.result_of(image_path)
        compared_detections: list[JsonValue] = (
            []
            if compared is None or compared_result is None
            else [self._detection(record, compared) for record in compared.records_of(image_path)]
        )
        compared_profile: DetectorProfile | None = workspace.compared_profile
        return {
            "path": str(image_path),
            "name": image_path.name,
            "version": None if info is None else info.version,
            "width": None if info is None else info.width,
            "height": None if info is None else info.height,
            "compared_model_name": None if compared_profile is None else compared_profile.model_name,
            "compared_detections": compared_detections,
        }

    @staticmethod
    def _detection(record: DetectionRecord, catalog: DetectionCatalog) -> JsonObject:
        box: list[JsonValue] = list(record.xyxy)
        return {
            "index": record.detection_index,
            "class_id": record.detection.class_id,
            "class_name": record.detection.class_name,
            "query": record.query_label,
            "confidence": float(record.detection.confidence),
            "box": box,
            "is_accepted": catalog.is_accepted(record),
        }

    def _model(self, selector: ModelSelector, selection: ModelSelection) -> JsonObject:
        backends: list[JsonValue] = []
        for backend in selector.backends:
            presets: list[JsonValue] = [
                {"name": preset.name, "label": preset.label} for preset in selector.presets_of(backend)
            ]
            backends.append(
                {
                    "value": backend.value,
                    "is_image_prompt_supported": PromptKind.VISUAL in backend.supported_prompt_kinds,
                    "presets": presets,
                }
            )
        devices: list[JsonValue] = [
            {
                "value": device.value,
                "is_available": selector.device_availability.is_available(device),
                "is_half_precision_supported": selector.device_availability.is_half_precision_supported(device),
            }
            for device in Device
        ]
        return {
            "backends": backends,
            "devices": devices,
            "selection": {
                "backend": selection.backend.value,
                "preset_name": selection.preset_name,
                "device": selection.device.value,
                "is_half_precision_enabled": selection.is_half_precision_enabled,
                "confidence_threshold": selection.confidence_threshold,
                "nms_iou_threshold": selection.nms_iou_threshold,
            },
        }

    @staticmethod
    def _profile(
        profile: DetectorProfile, image_count: int, outdated_image_count: int, detection_count: int
    ) -> JsonObject:
        return {
            "key": ProfileKey.of(profile),
            "backend": profile.backend.value,
            "model_name": profile.model_name,
            "weights_path": profile.weights_path,
            "device": profile.device.value,
            "precision": profile.precision_text,
            "confidence": profile.confidence_text,
            "nms": profile.nms_text,
            "options_text": profile.options_text,
            "image_count": image_count,
            "outdated_image_count": outdated_image_count,
            "detection_count": detection_count,
        }

    @staticmethod
    def _key_or_none(profile: DetectorProfile | None) -> str | None:
        return None if profile is None else ProfileKey.of(profile)

    def _classes(self, workbench: ClassWorkbench) -> list[JsonValue]:
        board: ReferenceBoard = workbench.reference_board
        return [
            self._class(index, definition.name, definition.text_queries, board)
            for index, definition in enumerate(workbench.classes)
        ]

    @staticmethod
    def _class(index: int, name: str, phrases: tuple[str, ...], board: ReferenceBoard) -> JsonObject:
        references: list[JsonValue] = []
        for reference_image in board.reference_images_of(name):
            width, height = board.pixels_of(reference_image).size
            boxes: list[JsonValue] = [list[JsonValue](box.xyxy) for box in board.boxes_of(name, reference_image)]
            references.append(
                {
                    "name": reference_image.name,
                    "digest": reference_image.digest,
                    "width": width,
                    "height": height,
                    "boxes": boxes,
                }
            )
        phrase_list: list[JsonValue] = list(phrases)
        return {
            "name": name,
            "color": ClassColors.hex_of(index),
            "phrases": phrase_list,
            "references": references,
        }

    @staticmethod
    def _class_set_state(workbench: ClassWorkbench) -> JsonObject:
        names: list[JsonValue] = list(workbench.class_set_store.class_set_names)
        return {
            "name": workbench.class_set_name,
            "is_edited": workbench.is_edited,
            "is_unsaved": workbench.is_unsaved,
            "names": names,
            "directory": str(workbench.class_set_store.class_set_directory),
        }

    @staticmethod
    def _thresholds(workspace: Workspace) -> JsonObject:
        class_minimums: JsonObject = dict(workspace.class_thresholds.class_minimums)
        return {"default_minimum": workspace.class_thresholds.default_minimum, "class_minimums": class_minimums}

    @staticmethod
    def _progress(progress: RunProgress | None) -> JsonValue:
        if progress is None:
            return None
        return {
            "title": progress.title,
            "processed_count": progress.processed_count,
            "total_count": progress.total_count,
            "is_blocking": progress.is_blocking,
        }

    @staticmethod
    def _export_report(report: ExportReport | None) -> JsonValue:
        if report is None:
            return None
        return {
            "format_name": report.format_name,
            "output_directory": str(report.output_directory),
            "image_count": report.image_count,
            "detection_count": report.detection_count,
            "file_count": report.file_count,
        }

    def _result_statistics(self, statistics: ResultStatistics) -> JsonObject:
        classes: list[JsonValue] = [self._class_statistics(entry) for entry in statistics.classes]
        return {
            "image_count": statistics.image_count,
            "detected_image_count": statistics.detected_image_count,
            "classes": classes,
            "histogram": self._histogram(ConfidenceHistogram.of(statistics.confidences)),
        }

    def _class_statistics(self, entry: ClassStatistics) -> JsonObject:
        return {
            "class_name": entry.class_name,
            "image_count": entry.image_count,
            "detection_count": entry.detection_count,
            "rejected_count": entry.rejected_count,
            "below_minimum_count": entry.below_minimum_count,
            "kept_count": entry.kept_count,
            "mean_confidence": entry.mean_confidence,
            "median_confidence": entry.median_confidence,
            "histogram": self._histogram(entry.histogram()),
        }

    @staticmethod
    def _histogram(histogram: ConfidenceHistogram) -> JsonObject:
        bin_counts: list[JsonValue] = list(histogram.bin_counts)
        return {"bin_counts": bin_counts, "bin_width": histogram.bin_width}

    @staticmethod
    def _comparison(comparison: ProfileComparison) -> JsonObject:
        classes: list[JsonValue] = [PayloadBuilder._class_comparison(entry) for entry in comparison.classes]
        return {"image_count": comparison.image_count, "iou_threshold": comparison.iou_threshold, "classes": classes}

    @staticmethod
    def _class_comparison(entry: ClassComparison) -> JsonObject:
        return {
            "class_name": entry.class_name,
            "baseline_count": entry.baseline_count,
            "candidate_count": entry.candidate_count,
            "matched_count": entry.matched_count,
            "baseline_only_count": entry.baseline_only_count,
            "candidate_only_count": entry.candidate_only_count,
        }
