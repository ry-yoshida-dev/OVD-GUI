import os
import weakref
from collections.abc import Callable
from pathlib import Path

from open_vocabulary_detector import DetectionResult, PromptQuery, TextQuery, VisualQuery, VisualReference
from PIL import Image

from ..detection import DetectionCatalog, DetectorProfile, LabeledPrompt, ReferenceImage, ResultLibrary
from .json_fields import JsonValue


class ResultManifestWriter:
    """
    Converts a ``ResultLibrary`` into the manifest of a ``ResultArchive``, collecting the reference images to store.

    Prompts shared by several images are written once. A reference image is identified by the label of its visual
    query and the digest of its pixels; digests are cached per ``VisualReference`` across writers sharing the cache.
    """

    def __init__(
        self,
        reference_identities: weakref.WeakKeyDictionary[VisualReference, ReferenceImage],
        image_file_of: Callable[[ReferenceImage], str],
    ) -> None:
        """
        Parameters
        ----------
        reference_identities : weakref.WeakKeyDictionary[VisualReference, ReferenceImage]
            Identity of every visual reference already hashed, filled while writing.
        image_file_of : Callable[[ReferenceImage], str]
            Archive entry holding the pixels of a reference image.
        """
        self._reference_identities: weakref.WeakKeyDictionary[VisualReference, ReferenceImage] = reference_identities
        self._image_file_of: Callable[[ReferenceImage], str] = image_file_of
        self._reference_images: dict[ReferenceImage, int] = {}
        self._reference_pixels: dict[ReferenceImage, Image.Image] = {}
        self._prompt_indices: dict[LabeledPrompt, int] = {}
        self._prompt_entries: list[JsonValue] = []

    @property
    def reference_pixels(self) -> dict[ReferenceImage, Image.Image]:
        """
        Pixels of every reference image a written visual query uses.

        Returns
        -------
        dict[ReferenceImage, Image.Image]
            Pixels per reference image, in the order they were first written.
        """
        return dict(self._reference_pixels)

    def manifest_of(self, library: ResultLibrary, format_name: str, format_version: int) -> dict[str, JsonValue]:
        """
        Build the manifest of a library.

        Parameters
        ----------
        library : ResultLibrary
            Results to write; images whose file cannot be found are left out.
        format_name : str
            Value of the ``format`` field.
        format_version : int
            Value of the ``version`` field.

        Returns
        -------
        dict[str, JsonValue]
            Manifest ready to be serialized.
        """
        profile_entries: list[JsonValue] = [
            self._profile_entry(profile, library.catalog_of(profile)) for profile in library.profiles
        ]
        return {
            "format": format_name,
            "version": format_version,
            "reference_images": [
                {
                    "name": reference_image.name,
                    "digest": reference_image.digest,
                    "file": self._file_entry(reference_image),
                }
                for reference_image in self._reference_images
            ],
            "prompts": self._prompt_entries,
            "profiles": profile_entries,
        }

    def _profile_entry(self, profile: DetectorProfile, catalog: DetectionCatalog) -> JsonValue:
        image_entries: list[JsonValue] = []
        for image_path in catalog.image_paths:
            result: DetectionResult | None = catalog.result_of(image_path)
            labeled_prompt: LabeledPrompt | None = catalog.labeled_prompt_of(image_path)
            if result is None or labeled_prompt is None or not image_path.is_file():
                continue
            image_entries.append(self._image_entry(image_path, result, labeled_prompt, catalog))
        return {
            "backend": profile.backend.value,
            "weights_path": profile.weights_path,
            "device": profile.device.value,
            "is_half_precision_enabled": profile.is_half_precision_enabled,
            "confidence_threshold": profile.thresholds.confidence_threshold,
            "nms_iou_threshold": profile.thresholds.nms_iou_threshold,
            "images": image_entries,
        }

    def _image_entry(
        self, image_path: Path, result: DetectionResult, labeled_prompt: LabeledPrompt, catalog: DetectionCatalog
    ) -> JsonValue:
        file_status: os.stat_result = image_path.stat()
        return {
            "path": str(image_path),
            "modified_ns": file_status.st_mtime_ns,
            "size": file_status.st_size,
            "width": result.image_size.width,
            "height": result.image_size.height,
            "prompt": self._prompt_index_of(labeled_prompt),
            "boxes": [[float(value) for value in box] for box in result.xyxy.tolist()],
            "confidences": [float(confidence) for confidence in result.confidences.tolist()],
            "query_ids": [int(query_id) for query_id in result.query_ids.tolist()],
            "rejected": [index for index in sorted(catalog.rejected_indices_of(image_path))],
        }

    def _prompt_index_of(self, labeled_prompt: LabeledPrompt) -> int:
        if labeled_prompt in self._prompt_indices:
            return self._prompt_indices[labeled_prompt]
        prompt_index: int = len(self._prompt_entries)
        self._prompt_indices[labeled_prompt] = prompt_index
        self._prompt_entries.append(self._prompt_entry(labeled_prompt))
        return prompt_index

    def _prompt_entry(self, labeled_prompt: LabeledPrompt) -> JsonValue:
        class_entries: list[JsonValue] = []
        query_id: int = 0
        for class_id, class_name in enumerate(labeled_prompt.prompt.class_names):
            query_entries: list[JsonValue] = []
            while (
                query_id < len(labeled_prompt.prompt.queries)
                and labeled_prompt.prompt.query_class_ids[query_id] == class_id
            ):
                query_entries.append(
                    self._query_entry(labeled_prompt.prompt.queries[query_id], labeled_prompt.query_labels[query_id])
                )
                query_id += 1
            class_entries.append({"name": class_name, "queries": query_entries})
        return {
            "classes": class_entries,
            "labels": list(labeled_prompt.query_labels),
            "signature": [
                {
                    "name": queried_class.name,
                    "phrases": [phrase for phrase in sorted(queried_class.phrases)],
                    "reference_boxes": [
                        {"image": self._reference_index_of(box.reference_image, None), "xyxy": list(box.xyxy)}
                        for box in sorted(
                            queried_class.reference_boxes, key=lambda box: (box.reference_image.digest, box.xyxy)
                        )
                    ],
                }
                for queried_class in labeled_prompt.signature.classes
            ],
        }

    def _query_entry(self, query: PromptQuery, label: str) -> JsonValue:
        match query:
            case TextQuery(text=text):
                return {"text": text}
            case VisualQuery(references=references):
                return {
                    "references": [
                        {
                            "image": self._reference_index_of(self._identity_of(reference, label), reference.image),
                            "boxes": [[float(value) for value in box] for box in reference.xyxy.tolist()],
                        }
                        for reference in references
                    ]
                }

    def _identity_of(self, reference: VisualReference, label: str) -> ReferenceImage:
        identity: ReferenceImage | None = self._reference_identities.get(reference)
        if identity is None or identity.name != label:
            identity = ReferenceImage.of(label, reference.image)
            self._reference_identities[reference] = identity
        return identity

    def _reference_index_of(self, reference_image: ReferenceImage, pixels: Image.Image | None) -> int:
        if pixels is not None and reference_image not in self._reference_pixels:
            self._reference_pixels[reference_image] = pixels
        return self._reference_images.setdefault(reference_image, len(self._reference_images))

    def _file_entry(self, reference_image: ReferenceImage) -> JsonValue:
        return self._image_file_of(reference_image) if reference_image in self._reference_pixels else None
