from collections.abc import Sequence
from dataclasses import replace
from typing import ClassVar

from open_vocabulary_detector import (
    DetectionResult,
    DetectionThresholds,
    DetectorBackend,
    DetectorSettings,
    Device,
    OpenVocabularyDetector,
    Prompt,
)
from PIL import Image

from ovd_gui.detection import DetectorSession


class FakeDetector(OpenVocabularyDetector):
    BACKEND: ClassVar[DetectorBackend] = DetectorBackend.YOLOE

    def _detect_mini_batch(self, images: Sequence[Image.Image], prompt: Prompt) -> list[DetectionResult]:
        return []


def _settings() -> DetectorSettings:
    return DetectorSettings(
        backend=DetectorBackend.YOLOE,
        weights_path="yoloe-26s-seg.pt",
        thresholds=DetectionThresholds(confidence_threshold=0.25, nms_iou_threshold=0.7),
    )


def test_empty_session_needs_loading() -> None:
    assert not DetectorSession().is_loaded_for(_settings())


def test_only_threshold_and_batch_changes_reuse_the_model() -> None:
    session: DetectorSession = DetectorSession()
    loaded_settings: DetectorSettings = _settings()
    session._detector = FakeDetector(loaded_settings)
    changed_settings: DetectorSettings = replace(
        loaded_settings, thresholds=DetectionThresholds(confidence_threshold=0.5, nms_iou_threshold=None), batch_size=1
    )
    assert session.is_loaded_for(changed_settings)
    assert not session.is_loaded_for(replace(loaded_settings, device=Device.CPU))
    assert not session.is_loaded_for(replace(loaded_settings, weights_path="yoloe-26n-seg.pt"))
    session.unload()
    assert session.loaded_settings is None
