from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExportReport:
    """
    What an export wrote.

    Attributes
    ----------
    format_name : str
        Display name of the annotation format.
    output_directory : Path
        Directory the files were written to.
    image_count : int
        Images with exported detections.
    detection_count : int
        Exported detections.
    file_count : int
        Annotation files written.
    annotated_image_count : int | None
        Images saved with their boxes drawn; ``None`` when they were not asked for.
    written_paths : tuple[Path, ...]
        Every file the export wrote: the annotation files, then the images saved with boxes drawn.
    """

    format_name: str
    output_directory: Path
    image_count: int
    detection_count: int
    file_count: int
    annotated_image_count: int | None
    written_paths: tuple[Path, ...]
