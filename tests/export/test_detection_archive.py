import json
from pathlib import Path

import numpy as np
import pytest
from object_detection_format import AnnotationDataset, AnnotationFormat, CocoWriter, PascalVocWriter, YoloWriter
from open_vocabulary_detector import DetectionResult, ImageSize, Prompt

from ovd_gui.export import DetectionArchive, ExportOptions


def _result(xyxy: list[list[float]], class_ids: list[int], class_names: tuple[str, ...]) -> DetectionResult:
    return DetectionResult.from_xyxy(
        xyxy=np.array(xyxy, dtype=np.float64).reshape(-1, 4),
        confidences=np.full(len(class_ids), 0.5, dtype=np.float64),
        query_ids=np.array(class_ids, dtype=np.int64),
        prompt=Prompt.from_class_names(class_names),
        image_size=ImageSize(width=100, height=50),
    )


def test_recording_again_replaces_the_result_and_keeps_order() -> None:
    archive: DetectionArchive = DetectionArchive()
    archive.record(Path("a.jpg"), _result([[0, 0, 10, 10]], [0], ("cat",)))
    archive.record(Path("b.jpg"), _result([], [], ("cat",)))
    archive.record(Path("a.jpg"), _result([[0, 0, 10, 10], [5, 5, 20, 20]], [0, 0], ("cat",)))
    dataset: AnnotationDataset = archive.build_dataset(())
    assert len(archive) == 2
    assert [image.image_path for image in dataset.images] == [Path("a.jpg"), Path("b.jpg")]
    assert len(dataset.images[0].objects) == 2
    assert dataset.images[1].objects == ()


def test_current_classes_come_first_then_classes_of_older_results() -> None:
    archive: DetectionArchive = DetectionArchive()
    archive.record(Path("a.jpg"), _result([[0, 0, 10, 10]], [0], ("old",)))
    dataset: AnnotationDataset = archive.build_dataset(("person", "car"))
    assert dataset.class_names == ("person", "car", "old")


def test_write_rejects_an_empty_archive(tmp_path: Path) -> None:
    options: ExportOptions = ExportOptions(
        annotation_format=AnnotationFormat.COCO, output_directory=tmp_path, is_confidence_included=True
    )
    with pytest.raises(ValueError, match="no detection results"):
        DetectionArchive().write(options, ())


def test_yolo_export_writes_labels_with_confidence(tmp_path: Path) -> None:
    archive: DetectionArchive = DetectionArchive()
    archive.record(Path("images/a.jpg"), _result([[0, 0, 50, 50]], [1], ("cat", "dog")))
    options: ExportOptions = ExportOptions(
        annotation_format=AnnotationFormat.YOLO, output_directory=tmp_path, is_confidence_included=True
    )
    written_paths: tuple[Path, ...] = archive.write(options, ("cat", "dog"))
    assert written_paths == (tmp_path / "a.txt", tmp_path / "classes.txt")
    assert (tmp_path / "a.txt").read_text().split() == ["1", "0.250000", "0.500000", "0.500000", "1.000000", "0.500000"]
    assert (tmp_path / "classes.txt").read_text().splitlines() == ["cat", "dog"]


def test_coco_export_omits_score_when_confidence_is_excluded(tmp_path: Path) -> None:
    archive: DetectionArchive = DetectionArchive()
    archive.record(Path("a.jpg"), _result([[10, 10, 30, 20]], [0], ("cat",)))
    options: ExportOptions = ExportOptions(
        annotation_format=AnnotationFormat.COCO, output_directory=tmp_path, is_confidence_included=False
    )
    (annotation_path,) = archive.write(options, ("cat",))
    document: dict[str, list[dict[str, object]]] = json.loads(annotation_path.read_text())
    assert document["annotations"][0]["bbox"] == [10.0, 10.0, 20.0, 10.0]
    assert "score" not in document["annotations"][0]


@pytest.mark.parametrize(
    ("annotation_format", "is_supported"),
    [
        (AnnotationFormat.COCO, True),
        (AnnotationFormat.YOLO, True),
        (AnnotationFormat.PASCAL_VOC, False),
        (AnnotationFormat.LABELME, False),
        (AnnotationFormat.CREATEML, False),
    ],
)
def test_confidence_support_per_format(annotation_format: AnnotationFormat, is_supported: bool) -> None:
    assert ExportOptions.is_confidence_supported(annotation_format) is is_supported


def test_writer_follows_format_and_confidence_setting(tmp_path: Path) -> None:
    yolo_writer: object = ExportOptions(AnnotationFormat.YOLO, tmp_path, is_confidence_included=True).create_writer()
    coco_writer: object = ExportOptions(AnnotationFormat.COCO, tmp_path, is_confidence_included=False).create_writer()
    voc_writer: object = ExportOptions(
        AnnotationFormat.PASCAL_VOC, tmp_path, is_confidence_included=True
    ).create_writer()
    assert isinstance(yolo_writer, YoloWriter) and yolo_writer.is_confidence_included
    assert isinstance(coco_writer, CocoWriter) and not coco_writer.is_confidence_included
    assert isinstance(voc_writer, PascalVocWriter)
