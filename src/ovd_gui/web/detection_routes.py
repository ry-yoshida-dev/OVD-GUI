import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, Response
from open_vocabulary_detector import DetectorBackend, Device

from ..detection import DetectionCatalog, DetectionRecord, DetectorProfile
from ..export import DetectionTableWriter
from ..review import ClassThresholds
from ..workspace import ModelSelection, Workspace
from .json_value import JsonObject
from .profile_key import ProfileKey
from .schema import (
    AcceptanceBody,
    ApprovalBody,
    ModelSelectionBody,
    PresetBody,
    ProfileBody,
    TableBody,
    ThresholdsBody,
)
from .web_context import WebContext


class DetectionRoutes:
    """
    Requests choosing the model, running detections, and reviewing and comparing the stored results.
    """

    CSV_FILE_NAME = "detections.csv"

    def __init__(self, context: WebContext) -> None:
        """
        Parameters
        ----------
        context : WebContext
            Shared workspace and helpers.
        """
        self._context: WebContext = context

    def router(self) -> APIRouter:
        """
        Routes of the detection requests.

        Returns
        -------
        APIRouter
            Router under ``/api``.
        """
        router: APIRouter = APIRouter(prefix="/api")
        context: WebContext = self._context

        @router.get("/state")
        async def state() -> JsonObject:
            return context.payloads.state(context.workspace)

        @router.get("/detections")
        async def detections() -> JsonObject:
            return context.payloads.detections(context.workspace)

        @router.get("/statistics")
        async def statistics() -> JsonObject:
            return context.payloads.statistics(context.workspace)

        @router.put("/model")
        async def select_model(body: ModelSelectionBody) -> JsonObject:
            context.workspace.select_model(
                ModelSelection(
                    backend=DetectorBackend(body.backend),
                    preset_name=body.preset_name,
                    device=Device(body.device),
                    is_half_precision_enabled=body.is_half_precision_enabled,
                    confidence_threshold=body.confidence_threshold,
                    nms_iou_threshold=body.nms_iou_threshold,
                )
            )
            return {}

        @router.put("/model/preset")
        async def select_preset(body: PresetBody) -> JsonObject:
            workspace: Workspace = context.workspace
            workspace.select_model(
                workspace.model_selector.selection_of(DetectorBackend(body.backend), body.preset_name)
            )
            return {}

        @router.post("/detect")
        async def detect(body: ApprovalBody) -> JsonObject:
            return context.payloads.reply(context.workspace.detect_current(body.is_skipping_approved))

        @router.post("/detect-all")
        async def detect_all(body: ApprovalBody) -> JsonObject:
            return context.payloads.reply(context.workspace.detect_all(body.is_skipping_approved))

        @router.post("/update-outdated")
        async def update_outdated(body: ApprovalBody) -> JsonObject:
            return context.payloads.reply(context.workspace.update_outdated(body.is_skipping_approved))

        @router.post("/cancel")
        async def cancel() -> JsonObject:
            context.workspace.cancel_batch()
            return {}

        @router.post("/profiles/select")
        async def select_profile(body: ProfileBody) -> JsonObject:
            workspace: Workspace = context.workspace
            workspace.select_profile(self._profile_of(workspace, body))
            return {}

        @router.post("/profiles/remove")
        async def remove_profile(body: ProfileBody) -> JsonObject:
            workspace: Workspace = context.workspace
            workspace.remove_profile(self._profile_of(workspace, body))
            return {}

        @router.post("/profiles/clear")
        async def clear_results() -> JsonObject:
            context.workspace.clear_results()
            return {}

        @router.put("/comparison")
        async def compare(body: ProfileBody) -> JsonObject:
            workspace: Workspace = context.workspace
            workspace.compare_with(None if body.key is None else self._profile_of(workspace, body))
            return {}

        @router.post("/detections/acceptance")
        async def set_acceptance(body: AcceptanceBody) -> JsonObject:
            context.workspace.set_accepted(
                {Path(path): indices for path, indices in body.detections.items()}, body.is_accepted
            )
            return {}

        @router.put("/thresholds")
        async def set_thresholds(body: ThresholdsBody) -> JsonObject:
            context.workspace.set_class_thresholds(ClassThresholds(body.default_minimum, body.class_minimums))
            return {}

        @router.post("/detections/csv")
        async def table_csv(body: TableBody) -> Response:
            catalog: DetectionCatalog | None = context.workspace.shown_catalog()
            if catalog is None:
                raise KeyError("No results are shown.")
            records: list[DetectionRecord] = []
            for reference in body.detections:
                image_records: tuple[DetectionRecord, ...] = catalog.records_of(Path(reference.path))
                if not 0 <= reference.index < len(image_records):
                    raise IndexError(f"No detection {reference.index} in {reference.path}.")
                records.append(image_records[reference.index])
            content: bytes = await asyncio.to_thread(self._table_csv, records, catalog)
            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{self.CSV_FILE_NAME}"'},
            )

        return router

    @staticmethod
    def _profile_of(workspace: Workspace, body: ProfileBody) -> DetectorProfile:
        if body.key is None:
            raise KeyError("No model given.")
        return ProfileKey.find(body.key, workspace.result_library.profiles)

    def _table_csv(self, records: list[DetectionRecord], catalog: DetectionCatalog) -> bytes:
        with tempfile.TemporaryDirectory() as directory:
            path: Path = Path(directory) / self.CSV_FILE_NAME
            DetectionTableWriter().write(records, catalog, path)
            return path.read_bytes()
