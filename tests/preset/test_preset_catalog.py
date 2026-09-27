from pathlib import Path

import pytest
from open_vocabulary_detector import DetectorBackend, DetectorSettings

from ovd_gui.preset import ModelPreset, PresetCatalog


def test_bundled_catalog_covers_every_backend() -> None:
    catalog: PresetCatalog = PresetCatalog.from_package()
    assert set(catalog.backends) == set(DetectorBackend)


def test_every_bundled_preset_builds_settings_of_its_backend() -> None:
    for preset in PresetCatalog.from_package().presets:
        settings: DetectorSettings = preset.load_settings()
        assert settings.backend is preset.backend


def test_preset_of_other_backend_is_rejected(tmp_path: Path) -> None:
    preset_file: Path = tmp_path / "mismatch.yaml"
    preset_file.write_text(
        "detector:\n  backend: yoloe\n  weights_path: yoloe-26s-seg.pt\n"
        + "  thresholds:\n    confidence_threshold: 0.25\n    nms_iou_threshold: 0.7\n"
    )
    with pytest.raises(ValueError, match="declares backend"):
        ModelPreset(backend=DetectorBackend.OWL_VIT, name="mismatch", source=preset_file).load_settings()


def test_preset_without_detector_section_is_rejected(tmp_path: Path) -> None:
    preset_file: Path = tmp_path / "empty.yaml"
    preset_file.write_text("other: {}\n")
    with pytest.raises(KeyError):
        ModelPreset(backend=DetectorBackend.YOLOE, name="empty", source=preset_file).load_settings()


def test_missing_root_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        PresetCatalog(tmp_path / "missing")
