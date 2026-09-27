from pathlib import Path

import pytest

from ovd_gui.storage import Session, SessionStore


def test_open_images_and_the_shown_one_are_remembered(tmp_path: Path) -> None:
    store: SessionStore = SessionStore(tmp_path / "data")
    assert store.load() == Session()
    session: Session = Session(image_paths=(tmp_path / "a.jpg", tmp_path / "b.jpg"), current_path=tmp_path / "b.jpg")
    store.save(session)
    assert store.load() == session
    store.save(Session())
    assert store.load() == Session()


@pytest.mark.parametrize(
    "content",
    ["not json", "[]", '{"images": "a.jpg"}', '{"images": [1]}', '{"images": ["a.jpg"], "current": "b.jpg"}'],
)
def test_unreadable_files_give_an_empty_session(tmp_path: Path, content: str) -> None:
    store: SessionStore = SessionStore(tmp_path)
    store.path.write_text(content, encoding="utf-8")
    assert store.load() == Session()


def test_the_shown_image_must_be_open() -> None:
    with pytest.raises(ValueError):
        Session(image_paths=(Path("a.jpg"),), current_path=Path("b.jpg"))
