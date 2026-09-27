import json
from pathlib import Path
from typing import ClassVar

from ..vocabulary import ClassListStore
from .json_fields import JsonFields, JsonValue
from .session import Session


class SessionStore:
    """
    Open images remembered between runs in ``session.json`` of a data directory.

    The file looks like ``{"images": ["/data/a.jpg", "/data/b.jpg"], "current": "/data/b.jpg"}``. The directory is
    created only when written to.
    """

    FILE_NAME: ClassVar[str] = "session.json"

    def __init__(self, root_directory: Path) -> None:
        """
        Parameters
        ----------
        root_directory : Path
            Data directory holding the file.
        """
        self._root_directory: Path = root_directory

    @classmethod
    def in_working_directory(cls) -> "SessionStore":
        """
        Build a store in the data directory under the current working directory.

        Returns
        -------
        SessionStore
            Store rooted at ``<cwd>/ovd_gui_data``.
        """
        return cls(Path.cwd() / ClassListStore.DEFAULT_DIRECTORY_NAME)

    @property
    def path(self) -> Path:
        """
        File holding the session.

        Returns
        -------
        Path
            ``session.json`` in the data directory, whether or not it exists.
        """
        return self._root_directory / self.FILE_NAME

    def load(self) -> Session:
        """
        Read the remembered session.

        Returns
        -------
        Session
            Stored session, or an empty one when nothing is stored or the file is unreadable.
        """
        if not self.path.is_file():
            return Session()
        try:
            content: dict[str, JsonValue] = JsonFields.object_of(
                JsonFields.parse(self.path.read_text(encoding="utf-8")), "session"
            )
            image_paths: tuple[Path, ...] = tuple(
                Path(JsonFields.string_of(image_path, "image path"))
                for image_path in JsonFields.list_of(content.get("images", []), "images")
            )
            current_value: JsonValue = content.get("current")
            current_path: Path | None = (
                None if current_value is None else Path(JsonFields.string_of(current_value, "current"))
            )
            return Session(image_paths=image_paths, current_path=current_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            return Session()

    def save(self, session: Session) -> None:
        """
        Remember a session for the next run.

        Parameters
        ----------
        session : Session
            Open images to store.

        Raises
        ------
        OSError
            If the data directory or the file cannot be written.
        """
        content: dict[str, JsonValue] = {
            "images": [str(image_path) for image_path in session.image_paths],
            "current": None if session.current_path is None else str(session.current_path),
        }
        self._root_directory.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
