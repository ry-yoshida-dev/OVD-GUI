import os
from pathlib import Path

import numpy as np
import pytest
from open_vocabulary_detector import (
    DetectionResult,
    DetectionThresholds,
    DetectorBackend,
    Device,
    ImageSize,
    PromptKind,
    TextQuery,
    VisualQuery,
)
from PIL import Image

from ovd_gui.detection import (
    DetectionCatalog,
    DetectorProfile,
    LabeledPrompt,
    ReferenceBoard,
    ReferenceBox,
    ReferenceImage,
    ResultLibrary,
)
from ovd_gui.storage import ResultArchive, ResultStore
from ovd_gui.vocabulary import ClassDefinition

VISUAL_PROFILE: DetectorProfile = DetectorProfile(
    backend=DetectorBackend.OWL_VIT,
    weights_path="google/owlvit-base-patch32",
    device=Device.AUTO,
    is_half_precision_enabled=False,
    thresholds=DetectionThresholds(confidence_threshold=0.1, nms_iou_threshold=None),
)
TEXT_PROFILE: DetectorProfile = DetectorProfile(
    backend=DetectorBackend.YOLO_WORLD,
    weights_path="yolov8s-worldv2.pt",
    device=Device.CPU,
    is_half_precision_enabled=True,
    thresholds=DetectionThresholds(confidence_threshold=0.25, nms_iou_threshold=0.7),
)


def _gradient(width: int, height: int) -> Image.Image:
    image: Image.Image = Image.new("RGB", (width, height))
    image.putdata([(x * 7 % 256, y * 11 % 256, (x + y) % 256) for y in range(height) for x in range(width)])
    return image


def _visual_prompt() -> LabeledPrompt:
    pixels: Image.Image = _gradient(40, 30)
    board: ReferenceBoard = ReferenceBoard()
    board.add(ReferenceBox(ReferenceImage.of("sedan.jpg", pixels), "car", 1.0, 2.0, 30.0, 25.0), pixels)
    return board.build_prompt(
        (ClassDefinition.parse("car: car, suv"), ClassDefinition.named("dog")),
        frozenset({PromptKind.TEXT, PromptKind.VISUAL}),
    )


def _result(labeled_prompt: LabeledPrompt, query_ids: list[int]) -> DetectionResult:
    count: int = len(query_ids)
    return DetectionResult.from_xyxy(
        xyxy=np.array([[index, index, index + 10.5, index + 20.0] for index in range(count)], dtype=np.float64),
        confidences=np.linspace(0.2, 0.8, count),
        query_ids=np.array(query_ids, dtype=np.int64),
        prompt=labeled_prompt.prompt,
        image_size=ImageSize(width=64, height=48),
    )


def _images(tmp_path: Path) -> tuple[Path, Path]:
    first: Path = tmp_path / "first.png"
    second: Path = tmp_path / "second.png"
    Image.new("RGB", (64, 48)).save(first)
    Image.new("RGB", (64, 48)).save(second)
    return first, second


def test_results_prompts_and_rejections_survive_a_round_trip(tmp_path: Path) -> None:
    first, second = _images(tmp_path)
    visual_prompt: LabeledPrompt = _visual_prompt()
    text_prompt: LabeledPrompt = ReferenceBoard().build_prompt(
        (ClassDefinition.named("cat"),), frozenset({PromptKind.TEXT})
    )
    library: ResultLibrary = ResultLibrary()
    library.record(VISUAL_PROFILE, first, _result(visual_prompt, [0, 2, 3]), visual_prompt)
    library.record(VISUAL_PROFILE, second, _result(visual_prompt, []), visual_prompt)
    library.record(TEXT_PROFILE, first, _result(text_prompt, [0]), text_prompt)
    library.catalog_of(VISUAL_PROFILE).set_accepted(first, (1,), is_accepted=False)
    archive: ResultArchive = ResultArchive(tmp_path / f"results{ResultArchive.SUFFIX}")
    archive.write(library)

    restored: ResultLibrary = ResultArchive(archive.path).read()
    assert restored.profiles == (VISUAL_PROFILE, TEXT_PROFILE)
    catalog: DetectionCatalog = restored.catalog_of(VISUAL_PROFILE)
    assert catalog.image_paths == (first, second)
    records = catalog.records_of(first)
    assert [(record.detection.class_name, record.query_label) for record in records] == [
        ("car", "car"),
        ("car", "sedan.jpg"),
        ("dog", "dog"),
    ]
    assert [catalog.is_accepted(record) for record in records] == [True, False, True]
    assert records[1].xyxy == (1.0, 1.0, 11.5, 21.0)
    assert catalog.labeled_prompt_of(first) is catalog.labeled_prompt_of(second)
    restored_prompt: LabeledPrompt | None = catalog.labeled_prompt_of(first)
    assert restored_prompt is not None
    assert restored_prompt.signature == visual_prompt.signature
    assert restored_prompt.prompt.queries[:2] == (TextQuery("car"), TextQuery("suv"))
    visual_query = restored_prompt.prompt.queries[2]
    assert isinstance(visual_query, VisualQuery)
    assert visual_query.references[0].image.tobytes() == _gradient(40, 30).tobytes()
    assert visual_query.references[0].xyxy.tolist() == [[1.0, 2.0, 30.0, 25.0]]
    assert restored.catalog_of(TEXT_PROFILE).records_of(first)[0].detection.class_name == "cat"


def test_results_of_changed_or_missing_image_files_are_dropped(tmp_path: Path) -> None:
    first, second = _images(tmp_path)
    text_prompt: LabeledPrompt = ReferenceBoard().build_prompt(
        (ClassDefinition.named("cat"),), frozenset({PromptKind.TEXT})
    )
    library: ResultLibrary = ResultLibrary()
    library.record(TEXT_PROFILE, first, _result(text_prompt, [0]), text_prompt)
    library.record(TEXT_PROFILE, second, _result(text_prompt, [0]), text_prompt)
    library.record(TEXT_PROFILE, tmp_path / "never_existed.png", _result(text_prompt, [0]), text_prompt)
    store: ResultStore = ResultStore(tmp_path / "data")
    store.save(library)

    Image.new("RGB", (64, 48), "white").save(first)
    os.utime(first, ns=(1, 1))
    second.unlink()
    restored: ResultLibrary = store.load()
    assert restored.profiles == (TEXT_PROFILE,)
    assert restored.catalog_of(TEXT_PROFILE).image_paths == ()


def test_missing_archive_loads_empty_and_foreign_files_are_rejected(tmp_path: Path) -> None:
    store: ResultStore = ResultStore(tmp_path / "data")
    assert store.load().profiles == ()
    store.path.parent.mkdir(parents=True)
    store.path.write_text("not a zip")
    with pytest.raises(ValueError):
        store.load()
