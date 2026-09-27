from dataclasses import dataclass
from pathlib import PurePosixPath

from open_vocabulary_detector import DetectionThresholds, DetectorBackend, DetectorSettings, Device


@dataclass(frozen=True)
class DetectorProfile:
    """
    Model and options a set of detection results was obtained with.

    Two runs share a profile when every setting that can change their detections is equal; the batch size is left
    out since it only affects speed.

    Attributes
    ----------
    backend : DetectorBackend
        Detector family.
    weights_path : str
        Checkpoint name or path of the model.
    device : Device
        Device the model ran on.
    is_half_precision_enabled : bool
        Whether the model ran in float16.
    thresholds : DetectionThresholds
        Confidence and NMS thresholds applied to the detections.
    """

    backend: DetectorBackend
    weights_path: str
    device: Device
    is_half_precision_enabled: bool
    thresholds: DetectionThresholds

    @classmethod
    def of(cls, settings: DetectorSettings) -> "DetectorProfile":
        """
        Profile of the results detected with some settings.

        Parameters
        ----------
        settings : DetectorSettings
            Settings of the detection run.

        Returns
        -------
        DetectorProfile
            Profile shared by every run whose detections these settings determine.
        """
        return cls(
            backend=settings.backend,
            weights_path=settings.weights_path,
            device=settings.device,
            is_half_precision_enabled=settings.is_half_precision_enabled,
            thresholds=settings.thresholds,
        )

    @property
    def model_name(self) -> str:
        """
        Short name of the model.

        Returns
        -------
        str
            Last component of the weights path without its file extension, e.g. ``"yolov8s-worldv2"``.
        """
        return PurePosixPath(self.weights_path).stem

    @property
    def options_text(self) -> str:
        """
        Device, precision and thresholds in one line.

        Returns
        -------
        str
            E.g. ``"auto · fp32 · conf 0.25 · NMS 0.70"``.
        """
        precision: str = "fp16" if self.is_half_precision_enabled else "fp32"
        nms_iou_threshold: float | None = self.thresholds.nms_iou_threshold
        nms_text: str = "off" if nms_iou_threshold is None else f"{nms_iou_threshold:.2f}"
        return f"{self.device.value} · {precision} · conf {self.thresholds.confidence_threshold:.2f} · NMS {nms_text}"
