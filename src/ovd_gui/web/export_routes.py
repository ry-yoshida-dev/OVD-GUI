import asyncio
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse
from object_detection_format import AnnotationFormat

from ..export import ExportOptions, ExportScope
from ..workspace import ExportReport, ExportRequest, Workspace
from .json_value import JsonObject
from .schema import ExportBody
from .web_context import WebContext


class ExportRoutes:
    """
    Requests exporting the stored results as annotation files, and downloading the written files.
    """

    EXPORT_DIRECTORY_NAME: ClassVar[str] = "exports"
    TIMESTAMP_FORMAT: ClassVar[str] = "%Y%m%d-%H%M%S"
    DEFAULT_ARCHIVE_STEM: ClassVar[str] = "export"

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
        Routes of the export requests.

        Returns
        -------
        APIRouter
            Router under ``/api``.
        """
        router: APIRouter = APIRouter(prefix="/api")
        context: WebContext = self._context

        @router.get("/export/plan")
        async def export_plan() -> JsonObject:
            workspace: Workspace = context.workspace
            default_directory: Path = (
                context.working_directory
                / self.EXPORT_DIRECTORY_NAME
                / datetime.now().astimezone().strftime(self.TIMESTAMP_FORMAT)
            )
            return context.payloads.export_plan(workspace.export_plan(), default_directory)

        @router.post("/export")
        async def export(body: ExportBody) -> JsonObject:
            options: ExportOptions = ExportOptions(
                annotation_format=AnnotationFormat(body.annotation_format),
                output_directory=Path(body.output_directory.strip()).expanduser().resolve(),
                is_confidence_included=body.is_confidence_included,
                scope=ExportScope(body.scope),
                minimum_confidence=body.minimum_confidence,
                is_annotated_image_saved=body.is_annotated_image_saved,
            )
            listed_indices: dict[Path, frozenset[int]] | None = (
                None
                if body.listed_indices is None
                else {Path(path): frozenset(indices) for path, indices in body.listed_indices.items()}
            )
            request: ExportRequest = ExportRequest(
                options=options, listed_indices=listed_indices, is_confidence_shown=body.is_confidence_shown
            )
            return context.payloads.reply(context.workspace.export(request, body.is_skipping_approved))

        @router.get("/export/download")
        async def download(background_tasks: BackgroundTasks) -> FileResponse:
            report: ExportReport | None = context.workspace.last_export
            if report is None:
                raise KeyError("Nothing has been exported yet.")
            staging_directory: Path = Path(tempfile.mkdtemp())
            background_tasks.add_task(shutil.rmtree, staging_directory, True)
            archive_name: str = f"{report.output_directory.name or self.DEFAULT_ARCHIVE_STEM}.zip"
            archive_path: Path = staging_directory / archive_name
            await asyncio.to_thread(self._zip, report, archive_path)
            return FileResponse(archive_path, filename=archive_name, media_type="application/zip")

        return router

    @staticmethod
    def _zip(report: ExportReport, archive_path: Path) -> None:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for written_path in report.written_paths:
                archive_member: Path = (
                    written_path.relative_to(report.output_directory)
                    if written_path.is_relative_to(report.output_directory)
                    else Path(written_path.name)
                )
                archive.write(written_path, archive_member.as_posix())
