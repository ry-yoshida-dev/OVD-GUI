import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile

from ..workspace import Workspace
from .image_preview import ImagePreview
from .json_value import JsonObject
from .schema import PathBody, PathsBody
from .web_context import WebContext


class ImageRoutes:
    """
    Requests opening, closing, showing and uploading images, and browsing the server for them.
    """

    PREVIEW_CACHE_CONTROL = "private, max-age=86400"

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
        Routes of the image requests.

        Returns
        -------
        APIRouter
            Router under ``/api``.
        """
        router: APIRouter = APIRouter(prefix="/api")
        context: WebContext = self._context

        @router.post("/images/open")
        async def open_images(body: PathsBody) -> JsonObject:
            context.workspace.open_paths([Path(path).expanduser() for path in body.paths])
            return {}

        @router.post("/images/close")
        async def close_images(body: PathsBody) -> JsonObject:
            context.workspace.close_images([Path(path) for path in body.paths])
            return {}

        @router.post("/images/select")
        async def select_image(body: PathBody) -> JsonObject:
            context.workspace.select_image(Path(body.path))
            return {}

        @router.post("/uploads")
        async def upload_images(
            files: Annotated[list[UploadFile], File()], is_first_shown: Annotated[bool, Query()] = True
        ) -> JsonObject:
            workspace: Workspace = context.workspace
            saved_paths: list[Path] = []
            for upload in files:
                content: bytes = await upload.read()
                saved_paths.append(
                    await asyncio.to_thread(workspace.stores.upload_store.save, upload.filename or "", content)
                )
            workspace.open_paths(saved_paths, is_first_shown)
            return {}

        @router.get("/image")
        async def image(path: str) -> Response:
            image_path: Path = Path(path)
            if image_path not in context.workspace.image_paths:
                raise KeyError(f"{image_path} is not open")
            preview: ImagePreview = await asyncio.to_thread(context.preview_cache.preview_of, image_path)
            return Response(
                content=preview.content,
                media_type=preview.media_type,
                headers={"Cache-Control": self.PREVIEW_CACHE_CONTROL},
            )

        @router.get("/files")
        async def files(path: Annotated[str | None, Query()] = None) -> JsonObject:
            return await asyncio.to_thread(context.browser.listing_of, None if path is None else Path(path))

        return router
