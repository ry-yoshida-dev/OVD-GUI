from pathlib import Path

import numpy as np
import pytest
from open_vocabulary_detector import DetectionResult, ImageSize, Prompt
from PIL import Image

from ovd_gui.export import AnnotatedImageWriter
from ovd_gui.media import LoadedImage


def _result(xyxy: list[list[float]], class_ids: list[int]) -> DetectionResult:
    return DetectionResult.from_xyxy(
        xyxy=np.array(xyxy, dtype=np.float64).reshape(-1, 4),
        confidences=np.full(len(class_ids), 0.8),
        query_ids=np.array(class_ids, dtype=np.int64),
        prompt=Prompt.from_class_names(("cat", "dog")),
        image_size=ImageSize(width=200, height=100),
    )


def _image(directory: Path, name: str) -> LoadedImage:
    directory.mkdir(parents=True, exist_ok=True)
    image_path: Path = directory / name
    Image.new("RGB", (200, 100), "black").save(image_path)
    return LoadedImage.open(image_path)


def test_boxes_are_drawn_in_the_color_of_their_class(tmp_path: Path) -> None:
    writer: AnnotatedImageWriter = AnnotatedImageWriter(("#ff0000", "#0000ff"), True, tmp_path / "out")
    written_path: Path = writer.write(
        _image(tmp_path / "images", "a.png"), _result([[10, 40, 60, 90], [100, 40, 150, 90]], [0, 1])
    )
    assert written_path == tmp_path / "out" / "a.png"
    with Image.open(written_path) as annotated:
        assert annotated.size == (200, 100)
        assert annotated.getpixel((10, 70)) == (255, 0, 0)
        assert annotated.getpixel((150, 70)) == (0, 0, 255)
        assert annotated.getpixel((35, 70)) == (0, 0, 0)


def test_images_sharing_a_name_are_numbered(tmp_path: Path) -> None:
    writer: AnnotatedImageWriter = AnnotatedImageWriter(("#ff0000",), False, tmp_path / "out")
    names: list[str] = [
        writer.write(_image(tmp_path / directory, "a.jpg"), _result([], [])).name for directory in ("x", "y", "z")
    ]
    assert names == ["a.jpg", "a_2.jpg", "a_3.jpg"]


def test_source_images_are_never_overwritten(tmp_path: Path) -> None:
    writer: AnnotatedImageWriter = AnnotatedImageWriter(("#ff0000",), False, tmp_path)
    with pytest.raises(ValueError):
        writer.write(_image(tmp_path, "a.png"), _result([], []))


def test_colors_are_required(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        AnnotatedImageWriter((), False, tmp_path)
