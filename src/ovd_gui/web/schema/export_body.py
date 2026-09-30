from pydantic import BaseModel


class ExportBody(BaseModel):
    """
    Options chosen in the export dialog.

    Attributes
    ----------
    annotation_format : str
        Value of the annotation format.
    output_directory : str
        Directory on the server receiving the files.
    is_confidence_included : bool
        Whether confidences are written, for formats that can store them.
    scope : str
        Value of the export scope: every kept detection or only the listed ones.
    minimum_confidence : float
        Detections below it are left out.
    is_annotated_image_saved : bool
        Whether the images are also saved with their boxes drawn.
    listed_indices : dict[str, list[int]] | None
        Detections listed in the detection table per image path; ``None`` when every detection is listed.
    is_confidence_shown : bool
        Whether the images saved with boxes label each box with its confidence.
    is_skipping_approved : bool
        Whether the user approved leaving out classes the model cannot query.
    """

    annotation_format: str
    output_directory: str
    is_confidence_included: bool
    scope: str
    minimum_confidence: float = 0.0
    is_annotated_image_saved: bool = False
    listed_indices: dict[str, list[int]] | None = None
    is_confidence_shown: bool = True
    is_skipping_approved: bool = False
