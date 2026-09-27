from dataclasses import dataclass
from pathlib import Path

from object_detection_format import (
    AnnotationFormat,
    AnnotationWriter,
    CocoWriter,
    CreateMlWriter,
    LabelMeWriter,
    PascalVocWriter,
    YoloWriter,
)


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
    """

    annotation_format: AnnotationFormat
    output_directory: Path
    is_confidence_included: bool

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
