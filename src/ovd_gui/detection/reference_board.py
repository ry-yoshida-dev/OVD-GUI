from collections.abc import Sequence
from pathlib import Path

import numpy as np
from geometry import Box2DFormat, Boxes2D
from open_vocabulary_detector import Prompt, PromptKind, PromptQuery, TextQuery, VisualQuery, VisualReference
from PIL import Image

from ..vocabulary import ClassDefinition
from .labeled_prompt import LabeledPrompt
from .reference_box import ReferenceBox

type ReferenceSignature = tuple[str, Path, tuple[tuple[float, float, float, float], ...]]


class ReferenceBoard:
    """
    Reference boxes drawn on reference images, turned into the prompt of a detection run.

    The boxes of one class on one reference image form one visual query (their embeddings are averaged); different
    images of a class are separate queries, so a sedan photo and a van photo are each matched on their own. Boxes are
    attached to class names, so they follow renames and stay valid when other classes are added or removed. A
    ``VisualReference`` is reused while its boxes are unchanged, which lets the detector reuse cached embeddings.
    """

    def __init__(self) -> None:
        self._boxes: list[ReferenceBox] = []
        self._images: dict[Path, Image.Image] = {}
        self._references: dict[ReferenceSignature, VisualReference] = {}

    @property
    def boxes(self) -> tuple[ReferenceBox, ...]:
        """
        Every reference box in drawing order.

        Returns
        -------
        tuple[ReferenceBox, ...]
            Boxes on all images.
        """
        return tuple(self._boxes)

    @property
    def is_empty(self) -> bool:
        """
        Whether no reference box exists.

        Returns
        -------
        bool
            True without any box.
        """
        return not self._boxes

    def reference_images_of(self, class_name: str) -> tuple[Path, ...]:
        """
        Reference images of one class, each one visual query.

        Parameters
        ----------
        class_name : str
            Class to look up.

        Returns
        -------
        tuple[Path, ...]
            Images holding boxes of the class, in the order their first box was added.
        """
        return tuple(dict.fromkeys(box.image_path for box in self._boxes if box.class_name == class_name))

    def boxes_of(self, class_name: str, image_path: Path) -> tuple[ReferenceBox, ...]:
        """
        Boxes of one class on one reference image.

        Parameters
        ----------
        class_name : str
            Class to look up.
        image_path : Path
            Reference image.

        Returns
        -------
        tuple[ReferenceBox, ...]
            Boxes in drawing order.
        """
        return tuple(box for box in self._boxes if box.class_name == class_name and box.image_path == image_path)

    def add(self, box: ReferenceBox, image: Image.Image) -> None:
        """
        Add a reference box.

        Parameters
        ----------
        box : ReferenceBox
            Box to add.
        image : Image.Image
            RGB pixels of ``box.image_path``, kept as long as the image has boxes.

        Raises
        ------
        ValueError
            If the box does not lie inside ``image``.
        """
        width, height = image.size
        if box.left < 0 or box.top < 0 or box.right > width or box.bottom > height:
            raise ValueError(f"box must lie inside the {width}x{height} image. got {box.xyxy}")
        self._boxes.append(box)
        self._images[box.image_path] = image

    def remove_reference_image(self, class_name: str, image_path: Path) -> None:
        """
        Remove the boxes of one class on one reference image, i.e. one visual query.

        Parameters
        ----------
        class_name : str
            Class of the boxes.
        image_path : Path
            Reference image of the boxes.
        """
        self._boxes = [
            box for box in self._boxes if not (box.class_name == class_name and box.image_path == image_path)
        ]
        self._forget_unused_images()

    def move_reference_image(self, class_name: str, image_path: Path, target_class_name: str) -> None:
        """
        Move the boxes of one class on one reference image to another class.

        The moved image joins the reference images of the target class, merging with its boxes on the same image.

        Parameters
        ----------
        class_name : str
            Class the boxes belong to.
        image_path : Path
            Reference image of the boxes.
        target_class_name : str
            Class to move the boxes to.
        """
        self._boxes = [
            box.renamed(target_class_name) if box.class_name == class_name and box.image_path == image_path else box
            for box in self._boxes
        ]

    def clear(self) -> None:
        """
        Remove every box.
        """
        self._boxes = []
        self._forget_unused_images()

    def rename_class(self, old_name: str, new_name: str) -> None:
        """
        Move the boxes of a renamed class to its new name.

        Parameters
        ----------
        old_name : str
            Previous class name.
        new_name : str
            Current class name.
        """
        self._boxes = [box.renamed(new_name) if box.class_name == old_name else box for box in self._boxes]

    def retain_classes(self, class_names: Sequence[str]) -> None:
        """
        Remove the boxes of classes that no longer exist.

        Parameters
        ----------
        class_names : Sequence[str]
            Current class names.
        """
        kept_names: frozenset[str] = frozenset(class_names)
        self._boxes = [box for box in self._boxes if box.class_name in kept_names]
        self._forget_unused_images()

    def build_prompt(
        self, definitions: Sequence[ClassDefinition], supported_kinds: frozenset[PromptKind]
    ) -> LabeledPrompt:
        """
        Prompt querying every class by its phrases and, when supported, by its reference images.

        Parameters
        ----------
        definitions : Sequence[ClassDefinition]
            Classes to detect, in class-id order.
        supported_kinds : frozenset[PromptKind]
            Query kinds the selected model accepts; reference images are left out without ``VISUAL``.

        Returns
        -------
        LabeledPrompt
            Prompt and the label of each query.

        Raises
        ------
        ValueError
            If there is no class, or a class is left without any query the model accepts.
        """
        is_visual_supported: bool = PromptKind.VISUAL in supported_kinds
        class_queries: dict[str, tuple[PromptQuery, ...]] = {}
        query_labels: list[str] = []
        used_references: dict[ReferenceSignature, VisualReference] = {}
        for definition in definitions:
            queries: list[PromptQuery] = [TextQuery(phrase) for phrase in definition.text_queries]
            query_labels.extend(definition.text_queries)
            image_paths: tuple[Path, ...] = self.reference_images_of(definition.name)
            if is_visual_supported:
                for image_path in image_paths:
                    signature: ReferenceSignature = self._signature_of(definition.name, image_path)
                    used_references[signature] = self._reference_for(signature)
                    queries.append(VisualQuery(references=(used_references[signature],)))
                    query_labels.append(image_path.name)
            if not queries:
                raise ValueError(self._describe_missing_queries(definition.name, has_references=bool(image_paths)))
            class_queries[definition.name] = tuple(queries)
        if not class_queries:
            raise ValueError("Add at least one class to detect.")
        self._references = used_references
        return LabeledPrompt(prompt=Prompt(class_queries), query_labels=tuple(query_labels))

    @staticmethod
    def _describe_missing_queries(class_name: str, has_references: bool) -> str:
        if has_references:
            return (
                f"'{class_name}' is queried only by reference images, which the selected model does not take. "
                + "Add a phrase to the class or choose OWL-ViT or YOLOE."
            )
        return f"'{class_name}' has no phrase and no reference image. Add a phrase to the class."

    def _signature_of(self, class_name: str, image_path: Path) -> ReferenceSignature:
        return (class_name, image_path, tuple(box.xyxy for box in self.boxes_of(class_name, image_path)))

    def _reference_for(self, signature: ReferenceSignature) -> VisualReference:
        cached: VisualReference | None = self._references.get(signature)
        if cached is not None:
            return cached
        _, image_path, xyxy = signature
        return VisualReference(
            image=self._images[image_path],
            boxes=Boxes2D.register(value=np.array(xyxy, dtype=np.float64), box2d_format=Box2DFormat.XYXY),
        )

    def _forget_unused_images(self) -> None:
        used_paths: frozenset[Path] = frozenset(box.image_path for box in self._boxes)
        self._images = {path: image for path, image in self._images.items() if path in used_paths}
