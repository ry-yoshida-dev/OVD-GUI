from collections.abc import Mapping, Sequence
from pathlib import Path

from open_vocabulary_detector import DetectionResult

from ..export import AnnotatedImageWriter, DetectionArchive, ExportOptions
from ..media import ClassColors, LoadedImage
from .export_report import ExportReport


class ExportWriter:
    """
    Writes selected detections as annotation files, and optionally the images with their boxes drawn.

    The writer only touches files, so it can run off the thread owning the workspace.
    """

    def __init__(self, is_confidence_shown: bool) -> None:
        """
        Parameters
        ----------
        is_confidence_shown : bool
            Whether the images saved with boxes label each box with its confidence.
        """
        self._is_confidence_shown: bool = is_confidence_shown

    def write(
        self,
        selected_results: Mapping[Path, DetectionResult],
        options: ExportOptions,
        class_names: Sequence[str],
    ) -> ExportReport:
        """
        Write the exported detections of every image.

        Parameters
        ----------
        selected_results : Mapping[Path, DetectionResult]
            Exported detections per image, in export order.
        options : ExportOptions
            Format, output directory and whether images with boxes are saved.
        class_names : Sequence[str]
            Current classes, in class-id order.

        Returns
        -------
        ExportReport
            Counts of what was written.

        Raises
        ------
        ValueError
            If the detections cannot be converted to the format.
        OSError
            If a file cannot be read or written.
        """
        archive: DetectionArchive = DetectionArchive()
        for image_path, result in selected_results.items():
            archive.record(image_path, result)
        written_paths: tuple[Path, ...] = archive.write(options, class_names)
        annotated_image_paths: list[Path] = []
        annotated_image_count: int | None = None
        if options.is_annotated_image_saved:
            image_writer: AnnotatedImageWriter = AnnotatedImageWriter(
                ClassColors.HEX_COLORS, self._is_confidence_shown, options.annotated_image_directory
            )
            for image_path, result in selected_results.items():
                annotated_image_paths.append(image_writer.write(LoadedImage.open(image_path), result))
            annotated_image_count = len(annotated_image_paths)
        return ExportReport(
            format_name=options.annotation_format.display_name,
            output_directory=options.output_directory,
            image_count=len(archive),
            detection_count=sum(len(result) for result in selected_results.values()),
            file_count=len(written_paths),
            annotated_image_count=annotated_image_count,
            written_paths=(*written_paths, *annotated_image_paths),
        )
