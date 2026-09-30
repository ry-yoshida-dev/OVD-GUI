from pathlib import Path

from ovd_gui.workspace import UploadStore


def test_uploaded_file_keeps_its_folder_inside_the_upload_directory(tmp_path: Path) -> None:
    store: UploadStore = UploadStore(tmp_path)
    saved: Path = store.save("trip/day1/a.jpg", b"pixels")
    assert saved == tmp_path / "uploads" / "trip" / "day1" / "a.jpg"
    assert saved.read_bytes() == b"pixels"


def test_same_content_reuses_the_stored_copy_and_other_content_gets_a_numbered_name(tmp_path: Path) -> None:
    store: UploadStore = UploadStore(tmp_path)
    first: Path = store.save("a.jpg", b"one")
    assert store.save("a.jpg", b"one") == first
    assert store.save("a.jpg", b"two").name == "a-1.jpg"
    assert store.save("a.jpg", b"two").name == "a-1.jpg"


def test_parts_leading_outside_the_directory_are_dropped(tmp_path: Path) -> None:
    store: UploadStore = UploadStore(tmp_path)
    assert store.save("../../etc\\passwd.png", b"x") == tmp_path / "uploads" / "etc" / "passwd.png"
    assert store.save("..", b"x") == tmp_path / "uploads" / "upload"
