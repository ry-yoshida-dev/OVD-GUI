import asyncio
import tempfile
from pathlib import Path
from typing import Annotated, ClassVar

from fastapi import APIRouter, File, Response, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

from ..detection import ReferenceBox, ReferenceImage
from ..media import LoadedImage
from ..storage import ClassSet
from ..vocabulary import ClassDefinition
from ..workspace import ClassWorkbench, Workspace
from .image_preview import ImagePreview
from .image_preview_cache import ImagePreviewCache
from .json_value import JsonObject
from .reference_draft import ReferenceDraft
from .schema import (
    ClassRowBody,
    MovePhraseBody,
    MoveReferenceBody,
    NameBody,
    PathBody,
    ReferenceBoxesBody,
    RemoveClassesBody,
    TextBody,
)
from .web_context import WebContext


class ClassRoutes:
    """
    Requests editing the classes, their phrases and reference images, and the saved class sets.
    """

    THUMBNAIL_SIDE: ClassVar[int] = 1024
    PREVIEW_CACHE_CONTROL: ClassVar[str] = "private, max-age=86400"

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
        Routes of the class requests.

        Returns
        -------
        APIRouter
            Router under ``/api``.
        """
        router: APIRouter = APIRouter(prefix="/api")
        context: WebContext = self._context

        @router.post("/classes/rows")
        async def add_row(body: ClassRowBody) -> JsonObject:
            class_index: int | None = body.class_index
            if class_index is None:
                context.workspace.edit_classes(lambda bench: bench.add_class(body.position, body.text))
            else:
                context.workspace.edit_classes(lambda bench: bench.add_phrases(class_index, body.position, body.text))
            return {}

        @router.put("/classes/{class_index}/name")
        async def rename_class(class_index: int, body: NameBody) -> JsonObject:
            context.workspace.edit_classes(lambda bench: bench.rename_class(class_index, body.name))
            return {}

        @router.put("/classes/{class_index}/phrases/{phrase_index}")
        async def rename_phrase(class_index: int, phrase_index: int, body: TextBody) -> JsonObject:
            context.workspace.edit_classes(lambda bench: bench.rename_phrase(class_index, phrase_index, body.text))
            return {}

        @router.post("/classes/remove")
        async def remove(body: RemoveClassesBody) -> JsonObject:
            phrase_indices: dict[int, list[int]] = {}
            for phrase in body.phrases:
                phrase_indices.setdefault(phrase.class_index, []).append(phrase.phrase_index)
            references: list[tuple[int, ReferenceImage]] = [
                (reference.class_index, ReferenceImage(name=reference.name, digest=reference.digest))
                for reference in body.references
            ]
            context.workspace.edit_classes(lambda bench: bench.remove(body.class_indices, phrase_indices, references))
            return {}

        @router.post("/classes/move-phrase")
        async def move_phrase(body: MovePhraseBody) -> JsonObject:
            target_class_index: int | None = body.target_class_index
            if target_class_index is None:
                context.workspace.edit_classes(
                    lambda bench: bench.promote_phrase(body.class_index, body.phrase_index, body.position)
                )
            else:
                context.workspace.edit_classes(
                    lambda bench: bench.move_phrase(
                        body.class_index, body.phrase_index, target_class_index, body.position
                    )
                )
            return {}

        @router.post("/classes/move-reference")
        async def move_reference(body: MoveReferenceBody) -> JsonObject:
            reference_image: ReferenceImage = ReferenceImage(name=body.name, digest=body.digest)
            context.workspace.edit_classes(
                lambda bench: bench.move_reference_image(body.class_index, reference_image, body.target_class_index)
            )
            return {}

        @router.put("/classes/text")
        async def replace_classes(body: TextBody) -> JsonObject:
            definitions: tuple[ClassDefinition, ...] = tuple(
                ClassDefinition.parse(line) for line in body.text.splitlines() if line.strip()
            )
            context.workspace.edit_classes(lambda bench: bench.set_classes(definitions))
            return {}

        @router.post("/classes/clear")
        async def clear_classes() -> JsonObject:
            context.workspace.edit_classes(lambda bench: bench.set_classes(()))
            return {}

        @router.post("/classes/file")
        async def load_class_file(file: Annotated[UploadFile, File()]) -> JsonObject:
            file_name: str = Path(file.filename or "classes.txt").name
            content: bytes = await file.read()
            with tempfile.TemporaryDirectory() as directory:
                path: Path = Path(directory) / file_name
                await asyncio.to_thread(path.write_bytes, content)
                context.workspace.edit_classes(lambda bench: bench.load_file(path, file_name))
            return {}

        @router.get("/references/image")
        async def reference_image(name: str, digest: str) -> Response:
            pixels: Image.Image = context.workspace.workbench.reference_board.pixels_of(
                ReferenceImage(name=name, digest=digest)
            )
            return await self._image_response(pixels, self.THUMBNAIL_SIDE)

        @router.post("/references/drafts")
        async def upload_reference(file: Annotated[UploadFile, File()]) -> JsonObject:
            file_name: str = Path(file.filename or "reference").name
            content: bytes = await file.read()
            with tempfile.TemporaryDirectory() as directory:
                path: Path = Path(directory) / file_name
                await asyncio.to_thread(path.write_bytes, content)
                loaded: LoadedImage = await asyncio.to_thread(LoadedImage.open, path)
            return self._draft_payload(context.drafts.add(file_name, loaded.image))

        @router.post("/references/drafts/path")
        async def open_reference(body: PathBody) -> JsonObject:
            path: Path = Path(body.path).expanduser()
            loaded: LoadedImage = await asyncio.to_thread(LoadedImage.open, path)
            return self._draft_payload(context.drafts.add(path.name, loaded.image))

        @router.get("/references/drafts/{draft_id}/image")
        async def draft_image(draft_id: str) -> Response:
            return await self._image_response(context.drafts.get(draft_id).image, ImagePreviewCache.MAX_SIDE)

        @router.post("/references")
        async def add_reference(body: ReferenceBoxesBody) -> JsonObject:
            workspace: Workspace = context.workspace
            draft: ReferenceDraft = context.drafts.get(body.draft_id)
            class_names: tuple[str, ...] = workspace.workbench.class_names
            if not 0 <= body.class_index < len(class_names):
                raise IndexError(f"No class {body.class_index}.")
            width, height = draft.image.size
            corners: list[list[float]] = body.boxes or [[0.0, 0.0, float(width), float(height)]]
            if any(len(corner) != 4 for corner in corners):
                raise ValueError("Every box needs four corners.")
            reference: ReferenceImage = ReferenceImage.of(draft.name, draft.image)
            boxes: tuple[ReferenceBox, ...] = tuple(
                ReferenceBox(
                    reference_image=reference,
                    class_name=class_names[body.class_index],
                    left=max(0.0, min(corner[0], corner[2])),
                    top=max(0.0, min(corner[1], corner[3])),
                    right=min(float(width), max(corner[0], corner[2])),
                    bottom=min(float(height), max(corner[1], corner[3])),
                )
                for corner in corners
            )
            workspace.edit_classes(lambda bench: bench.add_reference_boxes(boxes, draft.image))
            context.drafts.discard(body.draft_id)
            return {}

        @router.get("/class-sets")
        async def class_sets() -> JsonObject:
            return context.payloads.class_set_entries(context.workspace.workbench.class_set_store.entries)

        @router.get("/class-sets/{name}")
        async def class_set_preview(name: str) -> JsonObject:
            class_set: ClassSet = await asyncio.to_thread(
                context.workspace.workbench.class_set_store.read_class_set, name
            )
            return context.payloads.class_set_preview(name, class_set)

        @router.get("/class-sets/{name}/image")
        async def class_set_image(name: str, image_name: str, digest: str) -> Response:
            class_set: ClassSet = await asyncio.to_thread(
                context.workspace.workbench.class_set_store.read_class_set, name
            )
            return await self._image_response(
                class_set.reference_pixels[ReferenceImage(name=image_name, digest=digest)], self.THUMBNAIL_SIDE
            )

        @router.post("/class-sets/save")
        async def save_class_set(body: NameBody) -> JsonObject:
            context.workspace.edit_class_sets(lambda bench: bench.save_class_set(body.name))
            return {}

        @router.post("/class-sets/load")
        async def load_class_set(body: NameBody) -> JsonObject:
            context.workspace.edit_classes(lambda bench: bench.load_class_set(body.name))
            return {}

        @router.put("/class-sets/{name}")
        async def rename_class_set(name: str, body: NameBody) -> JsonObject:
            context.workspace.edit_class_sets(lambda bench: bench.rename_class_set(name, body.name))
            return {}

        @router.delete("/class-sets/{name}")
        async def delete_class_set(name: str) -> JsonObject:
            context.workspace.edit_class_sets(lambda bench: bench.class_set_store.delete_class_set(name))
            return {}

        @router.post("/class-sets/import")
        async def import_class_set(file: Annotated[UploadFile, File()]) -> JsonObject:
            file_name: str = Path(file.filename or "classes.ovdset").name
            content: bytes = await file.read()
            with tempfile.TemporaryDirectory() as directory:
                path: Path = Path(directory) / file_name
                await asyncio.to_thread(path.write_bytes, content)
                context.workspace.edit_class_sets(
                    lambda bench: self._import_class_set(bench, path, Path(file_name).stem)
                )
            return {}

        @router.get("/class-sets/{name}/file")
        async def export_class_set(name: str) -> FileResponse:
            path: Path = context.workspace.workbench.class_set_store.path_of(name)
            if not path.is_file():
                raise KeyError(f"No class set named '{name}'.")
            return FileResponse(path, filename=path.name, media_type="application/zip")

        return router

    @staticmethod
    def _import_class_set(bench: ClassWorkbench, path: Path, name: str) -> None:
        bench.class_set_store.import_archive(path, name)

    @staticmethod
    def _draft_payload(draft: ReferenceDraft) -> JsonObject:
        width, height = draft.image.size
        return {"draft_id": draft.draft_id, "name": draft.name, "width": width, "height": height}

    async def _image_response(self, pixels: Image.Image, max_side: int) -> Response:
        preview: ImagePreview = await asyncio.to_thread(ImagePreviewCache.encode, pixels, max_side)
        return Response(
            content=preview.content,
            media_type=preview.media_type,
            headers={"Cache-Control": self.PREVIEW_CACHE_CONTROL},
        )
