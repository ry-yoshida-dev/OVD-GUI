import json
from pathlib import Path
from typing import ClassVar

from ..review import ClassThresholds
from ..vocabulary import ClassListStore
from .json_fields import JsonFields, JsonValue


class ClassThresholdStore:
    """
    Minimum confidence per class, remembered between runs in ``class_thresholds.json`` of a data directory.

    The file looks like ``{"default": 0.0, "classes": {"car": 0.35}}``. The directory is created only when written
    to.
    """

    FILE_NAME: ClassVar[str] = "class_thresholds.json"

    def __init__(self, root_directory: Path) -> None:
        """
        Parameters
        ----------
        root_directory : Path
            Data directory holding the file.
        """
        self._root_directory: Path = root_directory

    @classmethod
    def in_working_directory(cls) -> "ClassThresholdStore":
        """
        Build a store in the data directory under the current working directory.

        Returns
        -------
        ClassThresholdStore
            Store rooted at ``<cwd>/ovd_gui_data``.
        """
        return cls(Path.cwd() / ClassListStore.DEFAULT_DIRECTORY_NAME)

    @property
    def path(self) -> Path:
        """
        File holding the thresholds.

        Returns
        -------
        Path
            ``class_thresholds.json`` in the data directory, whether or not it exists.
        """
        return self._root_directory / self.FILE_NAME

    def load(self) -> ClassThresholds:
        """
        Read the remembered thresholds.

        Returns
        -------
        ClassThresholds
            Stored thresholds, or thresholds keeping every detection when nothing is stored or the file is unreadable.
        """
        if not self.path.is_file():
            return ClassThresholds()
        try:
            content: dict[str, JsonValue] = JsonFields.object_of(
                JsonFields.parse(self.path.read_text(encoding="utf-8")), "thresholds"
            )
            class_minimums: dict[str, JsonValue] = JsonFields.object_of(content.get("classes", {}), "classes")
            return ClassThresholds(
                JsonFields.number_of(content.get("default", 0.0), "default"),
                {
                    class_name: JsonFields.number_of(minimum, class_name)
                    for class_name, minimum in class_minimums.items()
                },
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            return ClassThresholds()

    def save(self, thresholds: ClassThresholds) -> None:
        """
        Remember thresholds for the next run.

        Parameters
        ----------
        thresholds : ClassThresholds
            Thresholds to store.

        Raises
        ------
        OSError
            If the data directory or the file cannot be written.
        """
        content: dict[str, JsonValue] = {
            "default": thresholds.default_minimum,
            "classes": {class_name: minimum for class_name, minimum in thresholds.class_minimums.items()},
        }
        self._root_directory.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
