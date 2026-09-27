from pathlib import Path

import numpy as np
import pytest
from open_vocabulary_detector import DetectionResult, ImageSize, Prompt, TextQuery

from ovd_gui.detection import DetectionCatalog, DetectionRecord

PROMPT: Prompt = Prompt({"cat": (TextQuery("cat"),), "dog": (TextQuery("dog"), TextQuery("puppy"))})
QUERY_LABELS: tuple[str, ...] = ("cat", "dog", "puppy")


def _result(xyxy: list[list[float]], query_ids: list[int], confidences: list[float]) -> DetectionResult:
    return DetectionResult.from_xyxy(
        xyxy=np.array(xyxy, dtype=np.float64).reshape(-1, 4),
        confidences=np.array(confidences, dtype=np.float64),
        query_ids=np.array(query_ids, dtype=np.int64),
        prompt=PROMPT,
        image_size=ImageSize(width=100, height=50),
    )


def test_records_locate_each_detection_in_its_image() -> None:
    catalog: DetectionCatalog = DetectionCatalog()
    records: tuple[DetectionRecord, ...] = catalog.record(
        Path("a.jpg"), _result([[0, 0, 10, 10], [5, 6, 20, 30]], [0, 2], [0.9, 0.4]), QUERY_LABELS
    )
    assert [(record.image_path, record.detection_index) for record in records] == [
        (Path("a.jpg"), 0),
        (Path("a.jpg"), 1),
    ]
    assert records[1].detection.class_name == "dog"
    assert records[1].query_label == "puppy"
    assert records[1].xyxy == (5.0, 6.0, 20.0, 30.0)


def test_recording_again_replaces_the_image_and_keeps_order() -> None:
    catalog: DetectionCatalog = DetectionCatalog()
    catalog.record(Path("a.jpg"), _result([[0, 0, 10, 10]], [0], [0.9]), QUERY_LABELS)
    catalog.record(Path("b.jpg"), _result([[0, 0, 10, 10]], [1], [0.8]), QUERY_LABELS)
    catalog.record(Path("a.jpg"), _result([], [], []), QUERY_LABELS)
    assert len(catalog) == 2
    assert Path("a.jpg") in catalog
    assert catalog.records_of(Path("a.jpg")) == ()
    assert [record.image_path for record in catalog.records()] == [Path("b.jpg")]


def test_unknown_image_has_no_result_and_clear_forgets_everything() -> None:
    catalog: DetectionCatalog = DetectionCatalog()
    catalog.record(Path("a.jpg"), _result([[0, 0, 10, 10]], [0], [0.9]), QUERY_LABELS)
    assert catalog.result_of(Path("missing.jpg")) is None
    catalog.clear()
    assert catalog.result_of(Path("a.jpg")) is None
    assert catalog.records() == ()


def test_query_labels_must_match_the_prompt() -> None:
    with pytest.raises(ValueError, match="query labels"):
        DetectionCatalog().record(Path("a.jpg"), _result([], [], []), ("cat",))
