from pathlib import Path

import numpy as np
from open_vocabulary_detector import DetectionResult, ImageSize, PromptKind

from ovd_gui.analysis import ClassStatistics, ProfileComparison, ResultStatistics
from ovd_gui.detection import DetectionCatalog, LabeledPrompt, ReferenceBoard
from ovd_gui.review import ClassThresholds
from ovd_gui.vocabulary import ClassDefinition

LABELED_PROMPT: LabeledPrompt = ReferenceBoard().build_prompt(
    (ClassDefinition.named("cat"), ClassDefinition.named("dog")), frozenset({PromptKind.TEXT})
)


def _result(xyxy: list[list[float]], query_ids: list[int], confidences: list[float]) -> DetectionResult:
    return DetectionResult.from_xyxy(
        xyxy=np.array(xyxy, dtype=np.float64).reshape(-1, 4),
        confidences=np.array(confidences, dtype=np.float64),
        query_ids=np.array(query_ids, dtype=np.int64),
        prompt=LABELED_PROMPT.prompt,
        image_size=ImageSize(width=100, height=100),
    )


def _catalog() -> DetectionCatalog:
    catalog: DetectionCatalog = DetectionCatalog()
    catalog.record(
        Path("a.jpg"),
        _result([[0, 0, 10, 10], [20, 20, 40, 40], [50, 50, 60, 60]], [0, 0, 1], [0.9, 0.3, 0.6]),
        LABELED_PROMPT,
    )
    catalog.record(Path("b.jpg"), _result([[0, 0, 10, 10]], [0], [0.5]), LABELED_PROMPT)
    catalog.record(Path("closed.jpg"), _result([[0, 0, 10, 10]], [1], [0.5]), LABELED_PROMPT)
    return catalog


def test_statistics_count_rejected_and_below_minimum_detections_per_class() -> None:
    catalog: DetectionCatalog = _catalog()
    catalog.set_accepted(Path("a.jpg"), (0,), is_accepted=False)
    statistics: ResultStatistics = ResultStatistics.of(
        catalog,
        (Path("a.jpg"), Path("b.jpg"), Path("new.jpg")),
        ("cat", "dog", "bird"),
        ClassThresholds(0.0, {"cat": 0.4}),
    )
    assert statistics.image_count == 3
    assert statistics.detected_image_count == 2
    assert [entry.class_name for entry in statistics.classes] == ["cat", "dog", "bird"]
    cat: ClassStatistics | None = statistics.class_named("cat")
    assert cat is not None
    assert (cat.image_count, cat.detection_count, cat.rejected_count, cat.below_minimum_count, cat.kept_count) == (
        2,
        3,
        1,
        1,
        1,
    )
    assert cat.confidences == (0.3, 0.5, 0.9)
    assert cat.median_confidence == 0.5
    assert cat.histogram(10).bin_counts[3] == 1
    bird: ClassStatistics | None = statistics.class_named("bird")
    assert bird is not None and bird.mean_confidence is None
    assert statistics.confidences == (0.3, 0.5, 0.6, 0.9)


def test_classes_of_older_results_follow_the_current_ones() -> None:
    statistics: ResultStatistics = ResultStatistics.of(_catalog(), (Path("a.jpg"),), ("dog",), ClassThresholds())
    assert [entry.class_name for entry in statistics.classes] == ["dog", "cat"]


def test_profiles_are_compared_on_images_both_detected() -> None:
    baseline: DetectionCatalog = _catalog()
    candidate: DetectionCatalog = DetectionCatalog()
    candidate.record(
        Path("a.jpg"),
        _result([[1, 0, 11, 10], [70, 70, 90, 90], [50, 50, 60, 60]], [0, 0, 0], [0.8, 0.7, 0.6]),
        LABELED_PROMPT,
    )
    comparison: ProfileComparison = ProfileComparison.between(
        baseline, candidate, (Path("a.jpg"), Path("b.jpg")), ("cat", "dog")
    )
    assert comparison.image_count == 1
    cat, dog = comparison.classes
    assert (cat.baseline_count, cat.candidate_count, cat.matched_count) == (2, 3, 1)
    assert (cat.baseline_only_count, cat.candidate_only_count) == (1, 2)
    assert (dog.baseline_count, dog.candidate_count, dog.matched_count) == (1, 0, 0)
