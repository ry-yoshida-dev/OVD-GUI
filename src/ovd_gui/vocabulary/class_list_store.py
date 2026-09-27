from collections.abc import Iterable
from pathlib import Path

from .class_definition import ClassDefinition
from .class_list_file import ClassListFile


class ClassListStore:
    """
    Class lists kept in a data directory, typically ``ovd_gui_data`` under the working directory.

    The class list of the last run is remembered in ``last_classes.txt`` so that it can be restored at the next start;
    named class sets saved by the user go to ``classes/<name>.txt``. Directories are created only when written to.
    """

    DEFAULT_DIRECTORY_NAME = "ovd_gui_data"
    LAST_CLASSES_FILE_NAME = "last_classes.txt"
    CLASS_SET_DIRECTORY_NAME = "classes"
    CLASS_SET_SUFFIX = ".txt"
    FORBIDDEN_NAME_CHARACTERS: frozenset[str] = frozenset('/\\:*?"<>|')

    def __init__(self, root_directory: Path) -> None:
        """
        Parameters
        ----------
        root_directory : Path
            Data directory holding the remembered and saved class lists.
        """
        self._root_directory: Path = root_directory

    @classmethod
    def in_working_directory(cls) -> "ClassListStore":
        """
        Build a store in ``ovd_gui_data`` under the current working directory.

        Returns
        -------
        ClassListStore
            Store rooted at ``<cwd>/ovd_gui_data``.
        """
        return cls(Path.cwd() / cls.DEFAULT_DIRECTORY_NAME)

    @property
    def root_directory(self) -> Path:
        """
        Data directory.

        Returns
        -------
        Path
            Directory given at construction.
        """
        return self._root_directory

    @property
    def class_set_directory(self) -> Path:
        """
        Directory offered for saving and loading class lists.

        Returns
        -------
        Path
            ``classes`` sub-directory of the data directory.
        """
        return self._root_directory / self.CLASS_SET_DIRECTORY_NAME

    @property
    def class_set_names(self) -> tuple[str, ...]:
        """
        Names of the saved class sets.

        Returns
        -------
        tuple[str, ...]
            File stems in ``classes/``, sorted regardless of case.
        """
        if not self.class_set_directory.is_dir():
            return ()
        return tuple(
            sorted(
                (path.stem for path in self.class_set_directory.glob(f"*{self.CLASS_SET_SUFFIX}") if path.is_file()),
                key=str.casefold,
            )
        )

    def has_class_set(self, name: str) -> bool:
        """
        Whether a class set of this name is saved.

        Parameters
        ----------
        name : str
            Class set name.

        Returns
        -------
        bool
            True when ``classes/<name>.txt`` exists.

        Raises
        ------
        ValueError
            If the name is not usable as a file name.
        """
        return self._class_set_file(name).path.is_file()

    def read_class_set(self, name: str) -> tuple[ClassDefinition, ...]:
        """
        Read a saved class set.

        Parameters
        ----------
        name : str
            Class set name.

        Returns
        -------
        tuple[ClassDefinition, ...]
            Classes in class id order.

        Raises
        ------
        ValueError
            If the name is not usable as a file name or a line is not a valid class.
        OSError
            If the class set cannot be read.
        """
        return self._class_set_file(name).read()

    def write_class_set(self, name: str, definitions: Iterable[ClassDefinition]) -> None:
        """
        Save a class set, replacing one of the same name.

        Parameters
        ----------
        name : str
            Class set name.
        definitions : Iterable[ClassDefinition]
            Classes in class id order.

        Raises
        ------
        ValueError
            If the name is not usable as a file name.
        OSError
            If the class set cannot be written.
        """
        class_set_file: ClassListFile = self._class_set_file(name)
        self.class_set_directory.mkdir(parents=True, exist_ok=True)
        class_set_file.write(definitions)

    def load(self) -> tuple[ClassDefinition, ...] | None:
        """
        Read the class list remembered from the last run.

        Returns
        -------
        tuple[ClassDefinition, ...] | None
            Classes in class id order, or ``None`` when nothing has been remembered or the file is unreadable.
        """
        last_classes_file: ClassListFile = self._last_classes_file()
        if not last_classes_file.path.is_file():
            return None
        try:
            return last_classes_file.read()
        except (OSError, ValueError):
            return None

    def save(self, definitions: Iterable[ClassDefinition]) -> None:
        """
        Remember the class list for the next run.

        Parameters
        ----------
        definitions : Iterable[ClassDefinition]
            Classes in class id order.

        Raises
        ------
        OSError
            If the data directory or the file cannot be written.
        """
        self._root_directory.mkdir(parents=True, exist_ok=True)
        self._last_classes_file().write(definitions)

    def _class_set_file(self, name: str) -> ClassListFile:
        stripped_name: str = name.strip()
        if not stripped_name:
            raise ValueError("Class set name must not be blank.")
        if stripped_name.startswith(".") or any(
            character in self.FORBIDDEN_NAME_CHARACTERS or not character.isprintable() for character in stripped_name
        ):
            raise ValueError(f"Class set name must be a plain file name without a leading dot: {stripped_name!r}")
        return ClassListFile(self.class_set_directory / f"{stripped_name}{self.CLASS_SET_SUFFIX}")

    def _last_classes_file(self) -> ClassListFile:
        return ClassListFile(self._root_directory / self.LAST_CLASSES_FILE_NAME)
