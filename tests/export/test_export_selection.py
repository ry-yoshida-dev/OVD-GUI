from pathlib import Path

import numpy as np
import pytest
from open_vocabulary_detector import DetectionResult, ImageSize, PromptKind

from ovd_gui.detection import DetectionCatalog, LabeledPrompt, ReferenceBoard
from ovd_gui.export import ExportSelection
from ovd_gui.review import ClassThresholds
from ovd_gui.vocabulary import ClassDefinition

LABELED_PROMPT: LabeledPrompt = ReferenceBoard().build_prompt(
    (ClassDefinition.named("cat"), ClassDefinition.named("dog")), frozenset({PromptKind.TEXT})
)


def _catalog() -> DetectionCatalog:
    catalog: DetectionCatalog = DetectionCatalog()
    catalog.record(
        Path("a.jpg"),
        DetectionResult.from_xyxy(
            xyxy=np.tile(np.array([0.0, 0.0, 10.0, 10.0]), (4, 1)),
            confidences=np.array([0.2, 0.5, 0.7, 0.9]),
            query_ids=np.array([0, 1, 0, 1], dtype=np.int64),
            prompt=LABELED_PROMPT.prompt,
            image_size=ImageSize(width=100, height=50),
        ),
        LABELED_PROMPT,
    )
    catalog.set_accepted(Path("a.jpg"), (3,), is_accepted=False)
    return catalog


def test_rejected_and_below_minimum_detections_are_left_out() -> None:
    selection: ExportSelection = ExportSelection(ClassThresholds(0.0, {"cat": 0.6}), minimum_confidence=0.3)
    selected: DetectionResult | None = selection.selected_result(_catalog(), Path("a.jpg"))
    assert selected is not None
    assert selected.confidences.tolist() == [0.5, 0.7]
    assert selection.selected_result(_catalog(), Path("missing.jpg")) is None


def test_listed_indices_limit_the_export_to_the_table() -> None:
    selection: ExportSelection = ExportSelection(ClassThresholds(), listed_indices={Path("a.jpg"): frozenset({0, 3})})
    selected: DetectionResult | None = selection.selected_result(_catalog(), Path("a.jpg"))
    assert selected is not None
    assert selected.confidences.tolist() == [0.2]
    nothing_listed: ExportSelection = ExportSelection(ClassThresholds(), listed_indices={})
    empty: DetectionResult | None = nothing_listed.selected_result(_catalog(), Path("a.jpg"))
    assert empty is not None and len(empty) == 0


def test_minimum_outside_the_unit_interval_is_rejected() -> None:
    with pytest.raises(ValueError):
        ExportSelection(ClassThresholds(), minimum_confidence=1.5)
