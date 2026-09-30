from dataclasses import dataclass
from pathlib import Path

from ..detection import DetectionCatalog, DetectionRecord
from ..review import ClassThresholds
from .image_state import ImageState


@dataclass(frozen=True)
class ImageStatus:
    """
    State of one open image with the shown model, and how many of its detections are kept.

    Attributes
    ----------
    state : ImageState
        Whether the image is detected, outdated, failed or not analyzed yet.
    kept_count : int
        Detections neither rejected nor below the minimum confidence of their class; 0 when not detected.
    detection_count : int
        Every stored detection of the image; 0 when not detected.

    Raises
    ------
    ValueError
        If a count is negative or more detections are kept than stored.
    """

    state: ImageState
    kept_count: int = 0
    detection_count: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.kept_count <= self.detection_count:
            raise ValueError(
                f"kept_count must be in [0, detection_count]. got {self.kept_count} of {self.detection_count}"
            )

    @classmethod
    def of(
        cls,
        image_path: Path,
        catalog: DetectionCatalog | None,
        class_thresholds: ClassThresholds,
        is_outdated: bool,
        is_failed: bool,
    ) -> "ImageStatus":
        """
        Status of one image with the results of the shown model.

        Parameters
        ----------
        image_path : Path
            Open image.
        catalog : DetectionCatalog | None
            Results of the shown model; ``None`` while no model is shown.
        class_thresholds : ClassThresholds
            Minimum confidence of each class, deciding the kept detections.
        is_outdated : bool
            Whether the result was detected with other classes than the current ones.
        is_failed : bool
            Whether the last detection of the image with the current settings failed.

        Returns
        -------
        ImageStatus
            Failed when the image has no result and its detection failed, not analyzed when it has none otherwise,
            outdated or detected with its kept and stored counts when it has one.
        """
        if catalog is None or image_path not in catalog:
            return cls(ImageState.FAILED if is_failed else ImageState.NOT_ANALYZED)
        records: tuple[DetectionRecord, ...] = catalog.records_of(image_path)
        kept_count: int = sum(
            1
            for record in records
            if catalog.is_accepted(record)
            and class_thresholds.accepts(record.detection.class_name, record.detection.confidence)
        )
        return cls(
            ImageState.OUTDATED if is_outdated else ImageState.DETECTED,
            kept_count=kept_count,
            detection_count=len(records),
        )

    @property
    def count_text(self) -> str:
        """
        Count shown next to the image name.

        Returns
        -------
        str
            Kept detections, or ``kept/stored`` when some are hidden; empty when not detected.
        """
        match self.state:
            case ImageState.NOT_ANALYZED | ImageState.FAILED:
                return ""
            case ImageState.DETECTED | ImageState.OUTDATED:
                if self.kept_count == self.detection_count:
                    return str(self.kept_count)
                return f"{self.kept_count}/{self.detection_count}"

    @property
    def description(self) -> str:
        """
        Tool tip line describing the status.

        Returns
        -------
        str
            State with the kept and stored detection counts.
        """
        match self.state:
            case ImageState.NOT_ANALYZED | ImageState.FAILED:
                return self.state.description.capitalize()
            case ImageState.DETECTED | ImageState.OUTDATED:
                return (
                    f"{self.state.description.capitalize()}: {self.kept_count} of {self.detection_count} "
                    + "detections kept"
                )
