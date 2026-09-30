from dataclasses import dataclass

from open_vocabulary_detector import DetectorBackend, Device


@dataclass(frozen=True)
class ModelSelection:
    """
    Preset chosen in the model settings with the per-run overrides of its values.

    Attributes
    ----------
    backend : DetectorBackend
        Detector family of the preset.
    preset_name : str
        Preset name within the backend.
    device : Device
        Device to run on.
    is_half_precision_enabled : bool
        Whether to run the model in float16.
    confidence_threshold : float
        Minimum confidence of a detection, in ``[0, 1]``.
    nms_iou_threshold : float | None
        IoU threshold of non-maximum suppression in ``[0, 1]``; ``None`` disables it.

    Raises
    ------
    ValueError
        If a threshold is outside ``[0, 1]``.
    """

    backend: DetectorBackend
    preset_name: str
    device: Device
    is_half_precision_enabled: bool
    confidence_threshold: float
    nms_iou_threshold: float | None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(f"confidence_threshold must be in [0, 1]. got {self.confidence_threshold}")
        if self.nms_iou_threshold is not None and not 0.0 <= self.nms_iou_threshold <= 1.0:
            raise ValueError(f"nms_iou_threshold must be in [0, 1]. got {self.nms_iou_threshold}")
