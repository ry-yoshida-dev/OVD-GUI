from pathlib import Path

from ovd_gui.media import ImageCollection


def _touch(path: Path) -> Path:
    path.write_bytes(b"")
    return path


def test_folder_is_expanded_sorted_without_hidden_or_unsupported_files(tmp_path: Path) -> None:
    folder: Path = tmp_path / "images"
    folder.mkdir()
    second: Path = _touch(folder / "b.png")
    first: Path = _touch(folder / "a.JPG")
    _touch(folder / "._a.jpg")
    _touch(folder / "notes.txt")
    collection: ImageCollection = ImageCollection.gather([folder], [])
    assert collection.image_paths == (first.resolve(), second.resolve())
    assert collection.duplicate_count == 0
    assert collection.unsupported_count == 0


def test_known_and_repeated_images_are_counted_as_duplicates(tmp_path: Path) -> None:
    known: Path = _touch(tmp_path / "known.png").resolve()
    fresh: Path = _touch(tmp_path / "fresh.png")
    collection: ImageCollection = ImageCollection.gather([known, fresh, fresh], [known])
    assert collection.image_paths == (fresh.resolve(),)
    assert collection.duplicate_count == 2


def test_unsupported_files_make_an_empty_collection(tmp_path: Path) -> None:
    document: Path = _touch(tmp_path / "report.pdf")
    collection: ImageCollection = ImageCollection.gather([document, tmp_path / "missing.png"], [])
    assert collection.is_empty
    assert collection.unsupported_count == 2
