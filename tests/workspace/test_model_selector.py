from dataclasses import replace

import pytest
from open_vocabulary_detector import DetectorSettings, Device

from ovd_gui.detection import DeviceAvailability
from ovd_gui.preset import PresetCatalog
from ovd_gui.workspace import ModelSelection, ModelSelector

CPU_ONLY: DeviceAvailability = DeviceAvailability(is_cuda_available=False, is_mps_available=False)


def test_selection_of_a_preset_takes_its_values() -> None:
    selector: ModelSelector = ModelSelector(PresetCatalog.from_package(), CPU_ONLY)
    selection: ModelSelection = selector.default_selection()
    settings: DetectorSettings = selector.settings_of(selection)
    assert selection.backend == selector.backends[0]
    assert selection.confidence_threshold == settings.thresholds.confidence_threshold
    assert not selection.is_half_precision_enabled


def test_overrides_are_applied_to_the_preset_settings() -> None:
    selector: ModelSelector = ModelSelector(PresetCatalog.from_package(), CPU_ONLY)
    selection: ModelSelection = replace(selector.default_selection(), confidence_threshold=0.42, nms_iou_threshold=None)
    settings: DetectorSettings = selector.settings_of(selection)
    assert settings.thresholds.confidence_threshold == 0.42
    assert settings.thresholds.nms_iou_threshold is None


def test_validation_turns_off_float16_on_cpu_and_refuses_missing_devices() -> None:
    selector: ModelSelector = ModelSelector(PresetCatalog.from_package(), CPU_ONLY)
    half_on_cpu: ModelSelection = replace(
        selector.default_selection(), device=Device.CPU, is_half_precision_enabled=True
    )
    assert not selector.validated(half_on_cpu).is_half_precision_enabled
    with pytest.raises(ValueError, match="not available"):
        selector.validated(replace(selector.default_selection(), device=Device.CUDA))
    with pytest.raises(KeyError):
        selector.validated(replace(selector.default_selection(), preset_name="missing"))


def test_thresholds_outside_the_unit_range_are_rejected() -> None:
    selector: ModelSelector = ModelSelector(PresetCatalog.from_package(), CPU_ONLY)
    with pytest.raises(ValueError, match="confidence_threshold"):
        replace(selector.default_selection(), confidence_threshold=1.5)
