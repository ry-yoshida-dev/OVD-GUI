from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from open_vocabulary_detector import (
    DetectionResult,
    DetectionThresholds,
    DetectorBackend,
    DetectorSettings,
    Device,
    ImageSize,
    Prompt,
    PromptKind,
)

from ovd_gui.detection import DetectorProfile, LabeledPrompt, ProfileSummary, ReferenceBoard, ResultLibrary
from ovd_gui.vocabulary import ClassDefinition

SETTINGS: DetectorSettings = DetectorSettings(
    backend=DetectorBackend.YOLO_WORLD,
    weights_path="yolov8s-worldv2.pt",
    thresholds=DetectionThresholds(confidence_threshold=0.25, nms_iou_threshold=0.7),
    device=Device.CPU,
)


CAT_PROMPT: LabeledPrompt = ReferenceBoard().build_prompt((ClassDefinition.named("cat"),), frozenset({PromptKind.TEXT}))


def _result(count: int) -> DetectionResult:
    return DetectionResult.from_xyxy(
        xyxy=np.tile(np.array([0.0, 0.0, 10.0, 10.0]), (count, 1)),
        confidences=np.full(count, 0.5),
        query_ids=np.zeros(count, dtype=np.int64),
        prompt=Prompt.from_class_names(("cat",)),
        image_size=ImageSize(width=100, height=50),
    )


def test_profile_ignores_batch_size_but_not_model_or_thresholds() -> None:
    profile: DetectorProfile = DetectorProfile.of(SETTINGS)
    assert DetectorProfile.of(replace(SETTINGS, batch_size=8)) == profile
    assert DetectorProfile.of(replace(SETTINGS, weights_path="yolov8l-worldv2.pt")) != profile
    assert DetectorProfile.of(replace(SETTINGS, thresholds=DetectionThresholds(0.1, None))) != profile
    assert profile.model_name == "yolov8s-worldv2"
    assert profile.options_text == "cpu · fp32 · conf 0.25 · NMS 0.70"
    assert DetectorProfile.of(replace(SETTINGS, weights_path="IDEA-Research/grounding-dino-tiny")).model_name == (
        "grounding-dino-tiny"
    )


def test_results_of_each_profile_are_kept_apart() -> None:
    small: DetectorProfile = DetectorProfile.of(SETTINGS)
    large: DetectorProfile = DetectorProfile.of(replace(SETTINGS, weights_path="yolov8l-worldv2.pt"))
    library: ResultLibrary = ResultLibrary()
    library.record(small, Path("a.jpg"), _result(1), CAT_PROMPT)
    library.record(large, Path("a.jpg"), _result(3), CAT_PROMPT)
    library.record(large, Path("b.jpg"), _result(0), CAT_PROMPT)
    library.record(small, Path("a.jpg"), _result(2), CAT_PROMPT)
    assert library.profiles == (small, large)
    assert library.summaries(CAT_PROMPT.signature) == (
        ProfileSummary(profile=small, image_count=1, outdated_image_count=0, detection_count=2),
        ProfileSummary(profile=large, image_count=2, outdated_image_count=0, detection_count=3),
    )
    assert len(library.catalog_of(large).records_of(Path("a.jpg"))) == 3


def test_added_profile_starts_empty_and_removed_profiles_are_forgotten() -> None:
    profile: DetectorProfile = DetectorProfile.of(SETTINGS)
    library: ResultLibrary = ResultLibrary()
    assert len(library.add(profile)) == 0
    assert profile in library
    library.remove(profile)
    assert profile not in library
    with pytest.raises(KeyError):
        library.catalog_of(profile)
    library.add(profile)
    library.clear()
    assert library.profiles == ()
