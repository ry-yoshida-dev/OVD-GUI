from pydantic import BaseModel


class ModelSelectionBody(BaseModel):
    """
    Preset and overrides chosen in the model settings.

    Attributes
    ----------
    backend : str
        Value of the detector backend.
    preset_name : str
        Preset name within the backend.
    device : str
        Value of the device.
    is_half_precision_enabled : bool
        Whether to run in float16.
    confidence_threshold : float
        Minimum confidence of a detection.
    nms_iou_threshold : float | None
        IoU threshold of non-maximum suppression; ``None`` disables it.
    """

    backend: str
    preset_name: str
    device: str
    is_half_precision_enabled: bool
    confidence_threshold: float
    nms_iou_threshold: float | None
