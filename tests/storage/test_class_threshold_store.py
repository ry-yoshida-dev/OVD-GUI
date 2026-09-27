from pathlib import Path

from ovd_gui.review import ClassThresholds
from ovd_gui.storage import ClassThresholdStore


def test_thresholds_are_remembered(tmp_path: Path) -> None:
    store: ClassThresholdStore = ClassThresholdStore(tmp_path / "data")
    assert store.load() == ClassThresholds()
    store.save(ClassThresholds(0.1, {"car": 0.45}))
    assert ClassThresholdStore(tmp_path / "data").load() == ClassThresholds(0.1, {"car": 0.45})


def test_unreadable_files_load_as_keeping_every_detection(tmp_path: Path) -> None:
    store: ClassThresholdStore = ClassThresholdStore(tmp_path)
    for content in ("not json", '{"default": 2.0}', '{"classes": {"car": "high"}}', "[]"):
        store.path.write_text(content)
        assert store.load() == ClassThresholds()
