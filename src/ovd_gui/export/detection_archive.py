from collections.abc import Iterable
from pathlib import Path

from object_detection_format import AnnotationDataset, ImageAnnotation, ImageSize, ObjectAnnotation
from open_vocabulary_detector import DetectionResult

from .export_options import ExportOptions


class DetectionArchive:
    """
    Latest detection result of every image, ready to be exported as an annotation dataset.

    Recording an image again replaces its previous result; images keep the order in which they were first recorded.
    """

    def __init__(self) -> None:
        self._annotations: dict[Path, ImageAnnotation] = {}

    def __len__(self) -> int:
        return len(self._annotations)

    @property
    def is_empty(self) -> bool:
        """
        Whether no result has been recorded.

        Returns
        -------
        bool
            True when there is nothing to export.
        """
        return not self._annotations

    def record(self, image_path: Path, result: DetectionResult) -> None:
        """
        Store the result of one image, replacing an earlier one.

        Parameters
        ----------
        image_path : Path
            Image file the result was detected in.
        result : DetectionResult
            Detections with boxes in pixels of the upright image.
        """
        self._annotations[image_path] = ImageAnnotation(
            image_path=image_path,
            image_size=ImageSize(width=result.image_size.width, height=result.image_size.height),
            objects=tuple(
                ObjectAnnotation(box=detection.box, class_name=detection.class_name, confidence=detection.confidence)
                for detection in result
            ),
        )

    def clear(self) -> None:
        """
        Forget every recorded result.
        """
        self._annotations.clear()

    def build_dataset(self, class_names: Iterable[str]) -> AnnotationDataset:
        """
        Collect the recorded results into one dataset.

        Parameters
        ----------
        class_names : Iterable[str]
            Classes placed first in id order; classes found only in older results follow.

        Returns
        -------
        AnnotationDataset
            Recorded images, including those without detections.
        """
        return AnnotationDataset.from_images(self._annotations.values(), class_names=class_names)

    def write(self, options: ExportOptions, class_names: Iterable[str]) -> tuple[Path, ...]:
        """
        Export the recorded results.

        Parameters
        ----------
        options : ExportOptions
            Format, destination and confidence setting.
        class_names : Iterable[str]
            Classes placed first in id order.

        Raises
        ------
        ValueError
            If nothing is recorded, or the format writes one file per image and two images share a file stem.

        Returns
        -------
        tuple[Path, ...]
            Written files.
        """
        if self.is_empty:
            raise ValueError("no detection results to export")
        return options.create_writer().write(self.build_dataset(class_names), options.output_directory)
