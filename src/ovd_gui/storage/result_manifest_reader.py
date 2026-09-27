import io
import os
import zipfile
from pathlib import Path

import numpy as np
from geometry import Box2DFormat, Boxes2D
from open_vocabulary_detector import (
    DetectionResult,
    DetectionThresholds,
    DetectorBackend,
    Device,
    ImageSize,
    Prompt,
    PromptQuery,
    TextQuery,
    VisualQuery,
    VisualReference,
)
from PIL import Image

from ..detection import (
    DetectorProfile,
    LabeledPrompt,
    PromptSignature,
    QueriedClass,
    ReferenceBox,
    ReferenceImage,
    ResultLibrary,
)
from .json_fields import JsonFields, JsonValue


class ResultManifestReader:
    """
    Rebuilds a ``ResultLibrary`` from the manifest of a ``ResultArchive`` and the reference images it stores.

    Prompts are rebuilt once however many images share them, and a reference image is decoded once however many
    queries use it. Results of image files that are missing or whose modification time or size differs from the
    manifest are dropped; a profile left without results is still restored.
    """

    def __init__(self, archive: zipfile.ZipFile) -> None:
        """
        Parameters
        ----------
        archive : zipfile.ZipFile
            Open archive holding the reference images.
        """
        self._archive: zipfile.ZipFile = archive
        self._reference_images: list[ReferenceImage] = []
        self._reference_files: list[str | None] = []
        self._reference_pixels: dict[ReferenceImage, Image.Image] = {}
        self._prompt_entries: list[JsonValue] = []
        self._prompts: dict[int, LabeledPrompt] = {}

    def library_of(self, manifest: dict[str, JsonValue]) -> ResultLibrary:
        """
        Rebuild the stored results.

        Parameters
        ----------
        manifest : dict[str, JsonValue]
            Parsed manifest whose format has been checked.

        Returns
        -------
        ResultLibrary
            Profiles in stored order with the results of unchanged image files.

        Raises
        ------
        TypeError
            If a field has the wrong JSON type.
        KeyError
            If a reference image entry is missing from the archive.
        ValueError
            If a value is invalid, e.g. an index out of range or pixels not matching their digest.
        """
        for entry in JsonFields.list_of(manifest.get("reference_images"), "reference_images"):
            image_entry: dict[str, JsonValue] = JsonFields.object_of(entry, "reference image")
            self._reference_images.append(
                ReferenceImage(
                    name=JsonFields.string_of(image_entry.get("name"), "reference image name"),
                    digest=JsonFields.string_of(image_entry.get("digest"), "reference image digest"),
                )
            )
            file_entry: JsonValue = image_entry.get("file")
            self._reference_files.append(None if file_entry is None else JsonFields.string_of(file_entry, "file"))
        self._prompt_entries = JsonFields.list_of(manifest.get("prompts"), "prompts")
        library: ResultLibrary = ResultLibrary()
        for entry in JsonFields.list_of(manifest.get("profiles"), "profiles"):
            self._restore_profile(library, JsonFields.object_of(entry, "profile"))
        return library

    def _restore_profile(self, library: ResultLibrary, entry: dict[str, JsonValue]) -> None:
        nms_entry: JsonValue = entry.get("nms_iou_threshold")
        profile: DetectorProfile = DetectorProfile(
            backend=DetectorBackend(JsonFields.string_of(entry.get("backend"), "backend")),
            weights_path=JsonFields.string_of(entry.get("weights_path"), "weights_path"),
            device=Device(JsonFields.string_of(entry.get("device"), "device")),
            is_half_precision_enabled=JsonFields.boolean_of(
                entry.get("is_half_precision_enabled"), "is_half_precision_enabled"
            ),
            thresholds=DetectionThresholds(
                confidence_threshold=JsonFields.number_of(entry.get("confidence_threshold"), "confidence_threshold"),
                nms_iou_threshold=None if nms_entry is None else JsonFields.number_of(nms_entry, "nms_iou_threshold"),
            ),
        )
        library.add(profile)
        for image_entry in JsonFields.list_of(entry.get("images"), "images"):
            self._restore_image(library, profile, JsonFields.object_of(image_entry, "image"))

    def _restore_image(self, library: ResultLibrary, profile: DetectorProfile, entry: dict[str, JsonValue]) -> None:
        image_path: Path = Path(JsonFields.string_of(entry.get("path"), "image path"))
        if not self._is_unchanged(image_path, entry):
            return
        labeled_prompt: LabeledPrompt = self._prompt_at(JsonFields.integer_of(entry.get("prompt"), "prompt"))
        boxes: list[list[float]] = [
            [JsonFields.number_of(value, "box corner") for value in JsonFields.list_of(box, "box")]
            for box in JsonFields.list_of(entry.get("boxes"), "boxes")
        ]
        result: DetectionResult = DetectionResult(
            boxes=Boxes2D.register(
                value=np.array(boxes, dtype=np.float64).reshape(-1, 4), box2d_format=Box2DFormat.XYXY
            ),
            confidences=np.array(
                [
                    JsonFields.number_of(value, "confidence")
                    for value in JsonFields.list_of(entry.get("confidences"), "confidences")
                ],
                dtype=np.float64,
            ),
            query_ids=np.array(
                [
                    JsonFields.integer_of(value, "query id")
                    for value in JsonFields.list_of(entry.get("query_ids"), "query_ids")
                ],
                dtype=np.int64,
            ),
            prompt=labeled_prompt.prompt,
            image_size=ImageSize(
                width=JsonFields.integer_of(entry.get("width"), "width"),
                height=JsonFields.integer_of(entry.get("height"), "height"),
            ),
        )
        library.record(profile, image_path, result, labeled_prompt)
        rejected_indices: list[int] = [
            JsonFields.integer_of(value, "rejected index")
            for value in JsonFields.list_of(entry.get("rejected"), "rejected")
        ]
        if rejected_indices:
            try:
                library.catalog_of(profile).set_accepted(image_path, rejected_indices, is_accepted=False)
            except IndexError as error:
                raise ValueError(str(error)) from error

    @staticmethod
    def _is_unchanged(image_path: Path, entry: dict[str, JsonValue]) -> bool:
        try:
            file_status: os.stat_result = image_path.stat()
        except OSError:
            return False
        return file_status.st_mtime_ns == JsonFields.integer_of(
            entry.get("modified_ns"), "modified_ns"
        ) and file_status.st_size == JsonFields.integer_of(entry.get("size"), "size")

    def _prompt_at(self, prompt_index: int) -> LabeledPrompt:
        if prompt_index in self._prompts:
            return self._prompts[prompt_index]
        if not 0 <= prompt_index < len(self._prompt_entries):
            raise ValueError(f"prompt must index prompts. got {prompt_index}")
        entry: dict[str, JsonValue] = JsonFields.object_of(self._prompt_entries[prompt_index], "prompt")
        class_queries: dict[str, tuple[PromptQuery, ...]] = {}
        for class_entry in JsonFields.list_of(entry.get("classes"), "classes"):
            class_object: dict[str, JsonValue] = JsonFields.object_of(class_entry, "class")
            class_queries[JsonFields.string_of(class_object.get("name"), "class name")] = tuple(
                self._query_of(JsonFields.object_of(query, "query"))
                for query in JsonFields.list_of(class_object.get("queries"), "queries")
            )
        labeled_prompt: LabeledPrompt = LabeledPrompt(
            prompt=Prompt(class_queries),
            query_labels=tuple(
                JsonFields.string_of(label, "label") for label in JsonFields.list_of(entry.get("labels"), "labels")
            ),
            signature=PromptSignature(
                tuple(
                    self._queried_class_of(JsonFields.object_of(queried_class, "signature class"))
                    for queried_class in JsonFields.list_of(entry.get("signature"), "signature")
                )
            ),
        )
        self._prompts[prompt_index] = labeled_prompt
        return labeled_prompt

    def _query_of(self, entry: dict[str, JsonValue]) -> PromptQuery:
        if "text" in entry:
            return TextQuery(JsonFields.string_of(entry.get("text"), "query text"))
        return VisualQuery(
            references=tuple(
                self._reference_of(JsonFields.object_of(reference, "reference"))
                for reference in JsonFields.list_of(entry.get("references"), "references")
            )
        )

    def _reference_of(self, entry: dict[str, JsonValue]) -> VisualReference:
        reference_image: ReferenceImage = self._reference_image_at(JsonFields.integer_of(entry.get("image"), "image"))
        boxes: list[list[float]] = [
            [JsonFields.number_of(value, "box corner") for value in JsonFields.list_of(box, "box")]
            for box in JsonFields.list_of(entry.get("boxes"), "boxes")
        ]
        return VisualReference(
            image=self._pixels_of(reference_image),
            boxes=Boxes2D.register(
                value=np.array(boxes, dtype=np.float64).reshape(-1, 4), box2d_format=Box2DFormat.XYXY
            ),
        )

    def _queried_class_of(self, entry: dict[str, JsonValue]) -> QueriedClass:
        name: str = JsonFields.string_of(entry.get("name"), "signature class name")
        reference_boxes: list[ReferenceBox] = []
        for box_entry in JsonFields.list_of(entry.get("reference_boxes"), "reference_boxes"):
            box_object: dict[str, JsonValue] = JsonFields.object_of(box_entry, "reference box")
            corners: list[float] = [
                JsonFields.number_of(value, "box corner")
                for value in JsonFields.list_of(box_object.get("xyxy"), "xyxy")
            ]
            if len(corners) != 4:
                raise ValueError(f"reference box xyxy must hold 4 numbers. got {corners}")
            left, top, right, bottom = corners
            reference_boxes.append(
                ReferenceBox(
                    reference_image=self._reference_image_at(JsonFields.integer_of(box_object.get("image"), "image")),
                    class_name=name,
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                )
            )
        return QueriedClass(
            name=name,
            phrases=frozenset(
                JsonFields.string_of(phrase, "phrase") for phrase in JsonFields.list_of(entry.get("phrases"), "phrases")
            ),
            reference_boxes=frozenset(reference_boxes),
        )

    def _reference_image_at(self, image_index: int) -> ReferenceImage:
        if not 0 <= image_index < len(self._reference_images):
            raise ValueError(f"image must index reference_images. got {image_index}")
        return self._reference_images[image_index]

    def _pixels_of(self, reference_image: ReferenceImage) -> Image.Image:
        if reference_image in self._reference_pixels:
            return self._reference_pixels[reference_image]
        image_file: str | None = self._reference_files[self._reference_images.index(reference_image)]
        if image_file is None:
            raise ValueError(f"pixels of the reference image '{reference_image.name}' are not stored")
        with Image.open(io.BytesIO(self._archive.read(image_file))) as source:
            pixels: Image.Image = source.convert("RGB")
        if ReferenceImage.digest_of(pixels) != reference_image.digest:
            raise ValueError(f"pixels of the reference image '{reference_image.name}' do not match their digest")
        self._reference_pixels[reference_image] = pixels
        return pixels
