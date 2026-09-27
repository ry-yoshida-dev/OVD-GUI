import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from ..vocabulary import ClassListStore
from .class_set import ClassSet
from .class_set_archive import ClassSetArchive
from .class_set_entry import ClassSetEntry
from .class_set_summary import ClassSetSummary


class ClassSetStore:
    """
    Named class sets saved by the user, each one ``ClassSetArchive`` at ``classes/<name>.ovdset`` in a data directory.

    The directory is created only when a set is written to it.
    """

    CLASS_SET_DIRECTORY_NAME: ClassVar[str] = "classes"
    FORBIDDEN_NAME_CHARACTERS: ClassVar[frozenset[str]] = frozenset('/\\:*?"<>|')

    def __init__(self, root_directory: Path) -> None:
        """
        Parameters
        ----------
        root_directory : Path
            Data directory holding the ``classes`` sub-directory.
        """
        self._root_directory: Path = root_directory

    @classmethod
    def in_working_directory(cls) -> "ClassSetStore":
        """
        Build a store in the data directory under the current working directory.

        Returns
        -------
        ClassSetStore
            Store rooted at ``<cwd>/ovd_gui_data``, next to the remembered class list.
        """
        return cls(Path.cwd() / ClassListStore.DEFAULT_DIRECTORY_NAME)

    @property
    def class_set_directory(self) -> Path:
        """
        Directory holding the class sets.

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
            Stems of the ``.ovdset`` files in ``classes/``, sorted regardless of case.
        """
        if not self.class_set_directory.is_dir():
            return ()
        return tuple(
            sorted(
                (
                    path.stem
                    for path in self.class_set_directory.iterdir()
                    if path.is_file() and ClassSetArchive.is_archive_path(path)
                ),
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
            True when ``classes/<name>.ovdset`` exists.

        Raises
        ------
        ValueError
            If the name is not usable as a file name.
        """
        return self._archive_of(name).path.is_file()

    def read_class_set(self, name: str) -> ClassSet:
        """
        Read a saved class set.

        Parameters
        ----------
        name : str
            Class set name.

        Returns
        -------
        ClassSet
            Classes with their phrases and reference boxes.

        Raises
        ------
        ValueError
            If the name is not usable as a file name or the archive content is invalid.
        OSError
            If the class set cannot be read.
        """
        return self._archive_of(name).read()

    def write_class_set(self, name: str, class_set: ClassSet) -> None:
        """
        Save a class set, replacing one of the same name.

        Parameters
        ----------
        name : str
            Class set name.
        class_set : ClassSet
            Classes with their phrases and reference boxes.

        Raises
        ------
        ValueError
            If the name is not usable as a file name.
        OSError
            If the class set cannot be written.
        """
        archive: ClassSetArchive = self._archive_of(name)
        self.class_set_directory.mkdir(parents=True, exist_ok=True)
        archive.write(class_set)

    @property
    def entries(self) -> tuple[ClassSetEntry, ...]:
        """
        Every saved class set with its save time and counts.

        Returns
        -------
        tuple[ClassSetEntry, ...]
            Entries sorted by name regardless of case; unreadable files are listed without a summary.
        """
        return tuple(self._entry_of(name) for name in self.class_set_names)

    def path_of(self, name: str) -> Path:
        """
        File of a class set.

        Parameters
        ----------
        name : str
            Class set name.

        Returns
        -------
        Path
            ``classes/<name>.ovdset``, whether or not it exists.

        Raises
        ------
        ValueError
            If the name is not usable as a file name.
        """
        return self._archive_of(name).path

    def delete_class_set(self, name: str) -> None:
        """
        Delete a saved class set.

        Parameters
        ----------
        name : str
            Class set name.

        Raises
        ------
        ValueError
            If the name is not usable as a file name.
        FileNotFoundError
            If no class set of this name is saved.
        OSError
            If the file cannot be deleted.
        """
        self.path_of(name).unlink()

    def rename_class_set(self, name: str, new_name: str) -> None:
        """
        Rename a saved class set.

        Parameters
        ----------
        name : str
            Current class set name.
        new_name : str
            New class set name; a change of letter case only is allowed.

        Raises
        ------
        ValueError
            If either name is not usable as a file name.
        FileNotFoundError
            If no class set of ``name`` is saved.
        FileExistsError
            If another class set is already saved as ``new_name``.
        OSError
            If the file cannot be renamed.
        """
        source_path: Path = self.path_of(name)
        target_path: Path = self.path_of(new_name)
        if not source_path.is_file():
            raise FileNotFoundError(f"No class set named '{name.strip()}' is saved.")
        is_same_set: bool = new_name.strip().casefold() == name.strip().casefold()
        if target_path.exists() and not is_same_set:
            raise FileExistsError(f"A class set named '{new_name.strip()}' already exists.")
        source_path.rename(target_path)

    def import_archive(self, source_path: Path, name: str) -> None:
        """
        Copy a class set archive into the store, replacing a set of the same name.

        Parameters
        ----------
        source_path : Path
            ``.ovdset`` file to copy.
        name : str
            Name of the copied set.

        Raises
        ------
        ValueError
            If the name is not usable or the file is not a valid class set archive.
        OSError
            If the file cannot be read or copied.
        """
        target_path: Path = self.path_of(name)
        ClassSetArchive(source_path).read()
        self.class_set_directory.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target_path)

    def export_archive(self, name: str, target_path: Path) -> None:
        """
        Copy a saved class set to a file outside the store, e.g. to share it.

        Parameters
        ----------
        name : str
            Class set name.
        target_path : Path
            File to write, replaced if it exists.

        Raises
        ------
        ValueError
            If the name is not usable as a file name.
        OSError
            If the class set cannot be read or the file cannot be written.
        """
        shutil.copyfile(self.path_of(name), target_path)

    def _entry_of(self, name: str) -> ClassSetEntry:
        archive: ClassSetArchive = self._archive_of(name)
        summary: ClassSetSummary | None
        try:
            summary = archive.read_summary()
        except (OSError, ValueError):
            summary = None
        return ClassSetEntry(
            name=name,
            saved_at=datetime.fromtimestamp(archive.path.stat().st_mtime, tz=UTC).astimezone(),
            summary=summary,
        )

    def _archive_of(self, name: str) -> ClassSetArchive:
        stripped_name: str = name.strip()
        if not stripped_name:
            raise ValueError("Class set name must not be blank.")
        if stripped_name.startswith(".") or any(
            character in self.FORBIDDEN_NAME_CHARACTERS or not character.isprintable() for character in stripped_name
        ):
            raise ValueError(f"Class set name must be a plain file name without a leading dot: {stripped_name!r}")
        return ClassSetArchive(self.class_set_directory / f"{stripped_name}{ClassSetArchive.SUFFIX}")
