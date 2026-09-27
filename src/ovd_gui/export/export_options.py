from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from object_detection_format import (
    AnnotationFormat,
    AnnotationWriter,
    CocoWriter,
    CreateMlWriter,
    LabelMeWriter,
    PascalVocWriter,
    YoloWriter,
)

from .export_scope import ExportScope


@dataclass(frozen=True)
class ExportOptions:
    """
    How and where detection results are written.

    Attributes
    ----------
    annotation_format : AnnotationFormat
        Output format.
    output_directory : Path
        Directory receiving the files.
    is_confidence_included : bool
        Whether confidences are written; ignored by formats without a confidence field.
    scope : ExportScope
        Whether every kept detection is exported, or only those listed in the detection table.
    minimum_confidence : float
        Detections below this confidence are left out, in ``[0, 1]``; 0 keeps them all.
    is_annotated_image_saved : bool
        Whether the images are also saved with the exported detections drawn, in ``annotated_image_directory``.

    Raises
    ------
    ValueError
        If ``minimum_confidence`` is outside ``[0, 1]``.
    """

    annotation_format: AnnotationFormat
    output_directory: Path
    is_confidence_included: bool
    scope: ExportScope = ExportScope.KEPT
    minimum_confidence: float = 0.0
    is_annotated_image_saved: bool = False

    ANNOTATED_IMAGE_DIRECTORY_NAME: ClassVar[str] = "annotated_images"

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError(f"minimum_confidence must be in [0, 1]. got {self.minimum_confidence}")

    @property
    def annotated_image_directory(self) -> Path:
        """
        Directory receiving the images with the detections drawn.

        Returns
        -------
        Path
            ``annotated_images`` in the output directory.
        """
        return self.output_directory / self.ANNOTATED_IMAGE_DIRECTORY_NAME

    @staticmethod
    def is_confidence_supported(annotation_format: AnnotationFormat) -> bool:
        """
        Whether a format can store detection confidences.

        Parameters
        ----------
        annotation_format : AnnotationFormat
            Output format.

        Returns
        -------
        bool
            True for COCO (``score``) and YOLO (sixth column).
        """
        match annotation_format:
            case AnnotationFormat.COCO | AnnotationFormat.YOLO:
                return True
            case AnnotationFormat.PASCAL_VOC | AnnotationFormat.LABELME | AnnotationFormat.CREATEML:
                return False

    def create_writer(self) -> AnnotationWriter:
        """
        Build the writer of the chosen format.

        Returns
        -------
        AnnotationWriter
            Writer configured with these options.
        """
        match self.annotation_format:
            case AnnotationFormat.COCO:
                return CocoWriter(is_confidence_included=self.is_confidence_included)
            case AnnotationFormat.YOLO:
                return YoloWriter(is_confidence_included=self.is_confidence_included)
            case AnnotationFormat.PASCAL_VOC:
                return PascalVocWriter()
            case AnnotationFormat.LABELME:
                return LabelMeWriter()
            case AnnotationFormat.CREATEML:
                return CreateMlWriter()
