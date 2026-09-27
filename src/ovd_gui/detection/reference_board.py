from collections.abc import Mapping, Sequence

import numpy as np
from geometry import Box2DFormat, Boxes2D
from open_vocabulary_detector import Prompt, PromptKind, PromptQuery, TextQuery, VisualQuery, VisualReference
from PIL import Image

from ..vocabulary import ClassDefinition
from .labeled_prompt import LabeledPrompt
from .prompt_signature import PromptSignature
from .queried_class import QueriedClass
from .reference_box import ReferenceBox
from .reference_image import ReferenceImage

type ReferenceSignature = tuple[str, ReferenceImage, tuple[tuple[float, float, float, float], ...]]


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
        self._images: dict[ReferenceImage, Image.Image] = {}
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

    @property
    def reference_images(self) -> tuple[ReferenceImage, ...]:
        """
        Every image holding a box.

        Returns
        -------
        tuple[ReferenceImage, ...]
            Images in the order their first box was added.
        """
        return tuple(dict.fromkeys(box.reference_image for box in self._boxes))

    def reference_images_of(self, class_name: str) -> tuple[ReferenceImage, ...]:
        """
        Reference images of one class, each one visual query.

        Parameters
        ----------
        class_name : str
            Class to look up.

        Returns
        -------
        tuple[ReferenceImage, ...]
            Images holding boxes of the class, in the order their first box was added.
        """
        return tuple(dict.fromkeys(box.reference_image for box in self._boxes if box.class_name == class_name))

    def pixels_of(self, reference_image: ReferenceImage) -> Image.Image:
        """
        Pixels of a reference image.

        Parameters
        ----------
        reference_image : ReferenceImage
            Image holding at least one box.

        Returns
        -------
        Image.Image
            RGB pixels given when its boxes were added.

        Raises
        ------
        KeyError
            If no box lies on the image.
        """
        if reference_image not in self._images:
            raise KeyError(f"No reference box lies on '{reference_image.name}'.")
        return self._images[reference_image]

    def boxes_of(self, class_name: str, reference_image: ReferenceImage) -> tuple[ReferenceBox, ...]:
        """
        Boxes of one class on one reference image.

        Parameters
        ----------
        class_name : str
            Class to look up.
        reference_image : ReferenceImage
            Reference image.

        Returns
        -------
        tuple[ReferenceBox, ...]
            Boxes in drawing order.
        """
        return tuple(
            box for box in self._boxes if box.class_name == class_name and box.reference_image == reference_image
        )

    def add(self, box: ReferenceBox, image: Image.Image) -> None:
        """
        Add a reference box.

        Parameters
        ----------
        box : ReferenceBox
            Box to add.
        image : Image.Image
            RGB pixels of ``box.reference_image``, kept as long as the image has boxes.

        Raises
        ------
        ValueError
            If the box does not lie inside ``image``.
        """
        self._require_inside(box, image)
        self._boxes.append(box)
        self._images[box.reference_image] = image

    def replace(self, boxes: Sequence[ReferenceBox], pixels: Mapping[ReferenceImage, Image.Image]) -> None:
        """
        Replace every box, e.g. with the boxes of a loaded class set.

        Parameters
        ----------
        boxes : Sequence[ReferenceBox]
            New boxes in drawing order.
        pixels : Mapping[ReferenceImage, Image.Image]
            RGB pixels of every image the boxes lie on; images without a box are ignored.

        Raises
        ------
        KeyError
            If the pixels of an image are missing; the board is left unchanged.
        ValueError
            If a box does not lie inside its image; the board is left unchanged.
        """
        for box in boxes:
            if box.reference_image not in pixels:
                raise KeyError(f"Pixels of the reference image '{box.reference_image.name}' are missing.")
            self._require_inside(box, pixels[box.reference_image])
        self._boxes = list(boxes)
        self._images = {box.reference_image: pixels[box.reference_image] for box in boxes}

    def remove_reference_image(self, class_name: str, reference_image: ReferenceImage) -> None:
        """
        Remove the boxes of one class on one reference image, i.e. one visual query.

        Parameters
        ----------
        class_name : str
            Class of the boxes.
        reference_image : ReferenceImage
            Reference image of the boxes.
        """
        self._boxes = [
            box for box in self._boxes if not (box.class_name == class_name and box.reference_image == reference_image)
        ]
        self._forget_unused_images()

    def move_reference_image(self, class_name: str, reference_image: ReferenceImage, target_class_name: str) -> None:
        """
        Move the boxes of one class on one reference image to another class.

        The moved image joins the reference images of the target class, merging with its boxes on the same image.

        Parameters
        ----------
        class_name : str
            Class the boxes belong to.
        reference_image : ReferenceImage
            Reference image of the boxes.
        target_class_name : str
            Class to move the boxes to.
        """
        self._boxes = [
            box.renamed(target_class_name)
            if box.class_name == class_name and box.reference_image == reference_image
            else box
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

    def reference_only_classes(
        self, definitions: Sequence[ClassDefinition], supported_kinds: frozenset[PromptKind]
    ) -> tuple[str, ...]:
        """
        Classes queried only by reference images that the selected model cannot take.

        Parameters
        ----------
        definitions : Sequence[ClassDefinition]
            Classes to detect.
        supported_kinds : frozenset[PromptKind]
            Query kinds the selected model accepts.

        Returns
        -------
        tuple[str, ...]
            Names of classes without a phrase but with reference images, in class order; empty when the model
            accepts reference images.
        """
        if PromptKind.VISUAL in supported_kinds:
            return ()
        return tuple(
            definition.name
            for definition in definitions
            if not definition.text_queries and self.reference_images_of(definition.name)
        )

    def signature_of(self, definitions: Sequence[ClassDefinition]) -> PromptSignature:
        """
        What the classes query with their phrases and every reference box, whatever the model.

        Parameters
        ----------
        definitions : Sequence[ClassDefinition]
            Classes in class-id order.

        Returns
        -------
        PromptSignature
            Phrases and reference boxes of every class; narrow it to a model with
            ``PromptSignature.for_prompt_kinds``.
        """
        return PromptSignature(
            tuple(
                QueriedClass(
                    name=definition.name,
                    phrases=frozenset(definition.text_queries),
                    reference_boxes=frozenset(box for box in self._boxes if box.class_name == definition.name),
                )
                for definition in definitions
            )
        )

    def prompt_issue(
        self, definitions: Sequence[ClassDefinition], supported_kinds: frozenset[PromptKind]
    ) -> str | None:
        """
        Why no prompt can be built from the classes, checked before ``build_prompt``.

        Parameters
        ----------
        definitions : Sequence[ClassDefinition]
            Classes to detect.
        supported_kinds : frozenset[PromptKind]
            Query kinds the selected model accepts.

        Returns
        -------
        str | None
            Message for the user when there is no class or a class is left without any query the model accepts,
            ``None`` when a prompt can be built.
        """
        if not definitions:
            return "Add at least one class to detect."
        is_visual_supported: bool = PromptKind.VISUAL in supported_kinds
        for definition in definitions:
            has_references: bool = bool(self.reference_images_of(definition.name))
            if definition.text_queries or (is_visual_supported and has_references):
                continue
            return self._describe_missing_queries(definition.name, has_references=has_references)
        return None

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
            Prompt, the label of each query and the signature of what it queries.

        Raises
        ------
        ValueError
            If ``prompt_issue`` reports an issue.
        """
        issue: str | None = self.prompt_issue(definitions, supported_kinds)
        if issue is not None:
            raise ValueError(issue)
        is_visual_supported: bool = PromptKind.VISUAL in supported_kinds
        class_queries: dict[str, tuple[PromptQuery, ...]] = {}
        query_labels: list[str] = []
        used_references: dict[ReferenceSignature, VisualReference] = {}
        for definition in definitions:
            queries: list[PromptQuery] = [TextQuery(phrase) for phrase in definition.text_queries]
            query_labels.extend(definition.text_queries)
            reference_images: tuple[ReferenceImage, ...] = self.reference_images_of(definition.name)
            if is_visual_supported:
                for reference_image in reference_images:
                    signature: ReferenceSignature = self._signature_of(definition.name, reference_image)
                    used_references[signature] = self._reference_for(signature)
                    queries.append(VisualQuery(references=(used_references[signature],)))
                    query_labels.append(reference_image.name)
            class_queries[definition.name] = tuple(queries)
        self._references = used_references
        return LabeledPrompt(
            prompt=Prompt(class_queries),
            query_labels=tuple(query_labels),
            signature=self.signature_of(definitions).for_prompt_kinds(supported_kinds),
        )

    @staticmethod
    def _describe_missing_queries(class_name: str, has_references: bool) -> str:
        if has_references:
            return (
                f"'{class_name}' is queried only by reference images, which the selected model does not take. "
                + "Add a phrase to the class or choose OWL-ViT or YOLOE."
            )
        return f"'{class_name}' has no phrase and no reference image. Add a phrase to the class."

    @staticmethod
    def _require_inside(box: ReferenceBox, image: Image.Image) -> None:
        width, height = image.size
        if box.left < 0 or box.top < 0 or box.right > width or box.bottom > height:
            raise ValueError(f"box must lie inside the {width}x{height} image. got {box.xyxy}")

    def _signature_of(self, class_name: str, reference_image: ReferenceImage) -> ReferenceSignature:
        return (
            class_name,
            reference_image,
            tuple(box.xyxy for box in self.boxes_of(class_name, reference_image)),
        )

    def _reference_for(self, signature: ReferenceSignature) -> VisualReference:
        cached: VisualReference | None = self._references.get(signature)
        if cached is not None:
            return cached
        _, reference_image, xyxy = signature
        return VisualReference(
            image=self._images[reference_image],
            boxes=Boxes2D.register(value=np.array(xyxy, dtype=np.float64), box2d_format=Box2DFormat.XYXY),
        )

    def _forget_unused_images(self) -> None:
        used_images: frozenset[ReferenceImage] = frozenset(box.reference_image for box in self._boxes)
        self._images = {
            reference_image: image for reference_image, image in self._images.items() if reference_image in used_images
        }
