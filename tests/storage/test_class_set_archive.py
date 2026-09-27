import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from ovd_gui.detection import ReferenceBox, ReferenceImage
from ovd_gui.storage import ClassSet, ClassSetArchive
from ovd_gui.vocabulary import ClassDefinition


def _gradient(width: int, height: int) -> Image.Image:
    image: Image.Image = Image.new("RGB", (width, height))
    image.putdata([(x * 7 % 256, y * 11 % 256, (x + y) % 256) for y in range(height) for x in range(width)])
    return image


def _class_set() -> ClassSet:
    sedan_pixels: Image.Image = _gradient(40, 30)
    van_pixels: Image.Image = _gradient(20, 20)
    sedan: ReferenceImage = ReferenceImage.of("sedan.jpg", sedan_pixels)
    van: ReferenceImage = ReferenceImage.of("van.png", van_pixels)
    return ClassSet(
        classes=(ClassDefinition.parse("car: car, suv"), ClassDefinition.parse("mug:"), ClassDefinition.named("dog")),
        reference_boxes=(
            ReferenceBox(sedan, "car", 1.5, 2.0, 30.0, 25.0),
            ReferenceBox(van, "mug", 0.0, 0.0, 20.0, 20.0),
            ReferenceBox(sedan, "car", 5.0, 5.0, 10.0, 10.0),
        ),
        reference_pixels={sedan: sedan_pixels, van: van_pixels},
    )


def _rewrite_manifest(path: Path, manifest: dict[str, object]) -> None:
    with zipfile.ZipFile(path) as archive:
        entries: dict[str, bytes] = {name: archive.read(name) for name in archive.namelist()}
    entries[ClassSetArchive.MANIFEST_NAME] = json.dumps(manifest).encode()
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def _manifest_of(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        manifest: object = json.loads(archive.read(ClassSetArchive.MANIFEST_NAME))
    assert isinstance(manifest, dict)
    return {str(key): value for key, value in manifest.items()}


def test_round_trip_restores_classes_boxes_and_pixels(tmp_path: Path) -> None:
    original: ClassSet = _class_set()
    archive: ClassSetArchive = ClassSetArchive(tmp_path / "vehicles.ovdset")
    archive.write(original)
    restored: ClassSet = archive.read()
    assert restored.classes == original.classes
    assert restored.reference_boxes == original.reference_boxes
    for reference_image in original.reference_images:
        assert (
            restored.reference_pixels[reference_image].tobytes() == original.reference_pixels[reference_image].tobytes()
        )


def test_archive_holds_a_manifest_and_one_png_per_image(tmp_path: Path) -> None:
    path: Path = tmp_path / "vehicles.ovdset"
    ClassSetArchive(path).write(_class_set())
    with zipfile.ZipFile(path) as archive:
        names: set[str] = set(archive.namelist())
    image_names: set[str] = names - {ClassSetArchive.MANIFEST_NAME}
    assert ClassSetArchive.MANIFEST_NAME in names
    assert len(image_names) == 2
    assert all(name.startswith("images/") and name.endswith(".png") for name in image_names)
    assert not list(tmp_path.glob("*.partial"))


def test_set_without_references_is_written_and_read(tmp_path: Path) -> None:
    archive: ClassSetArchive = ClassSetArchive(tmp_path / "plain.ovdset")
    archive.write(ClassSet(classes=(ClassDefinition.named("cat"),)))
    assert archive.read().classes == (ClassDefinition.named("cat"),)


def test_non_archive_is_rejected(tmp_path: Path) -> None:
    path: Path = tmp_path / "broken.ovdset"
    path.write_text("cat\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a class set archive"):
        ClassSetArchive(path).read()


def test_foreign_manifest_is_rejected(tmp_path: Path) -> None:
    path: Path = tmp_path / "foreign.ovdset"
    ClassSetArchive(path).write(_class_set())
    _rewrite_manifest(path, {"format": "something-else", "version": 1})
    with pytest.raises(ValueError, match="not an OVD GUI class set"):
        ClassSetArchive(path).read()


def test_malformed_manifest_is_reported_as_value_error(tmp_path: Path) -> None:
    path: Path = tmp_path / "malformed.ovdset"
    ClassSetArchive(path).write(_class_set())
    manifest: dict[str, object] = _manifest_of(path)
    manifest["classes"] = [{"name": 3, "phrases": []}]
    _rewrite_manifest(path, manifest)
    with pytest.raises(ValueError, match="malformed"):
        ClassSetArchive(path).read()


def test_tampered_pixels_are_rejected(tmp_path: Path) -> None:
    path: Path = tmp_path / "tampered.ovdset"
    ClassSetArchive(path).write(_class_set())
    manifest: dict[str, object] = _manifest_of(path)
    images: object = manifest["reference_images"]
    assert isinstance(images, list)
    first_image: object = images[0]
    second_image: object = images[1]
    assert isinstance(first_image, dict)
    assert isinstance(second_image, dict)
    first_image["file"] = second_image["file"]
    _rewrite_manifest(path, manifest)
    with pytest.raises(ValueError, match="do not match their digest"):
        ClassSetArchive(path).read()


def test_archive_suffix_is_recognised_regardless_of_case() -> None:
    assert ClassSetArchive.is_archive_path(Path("a/b.OVDSET"))
    assert not ClassSetArchive.is_archive_path(Path("classes.txt"))
