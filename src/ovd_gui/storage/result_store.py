from pathlib import Path
from typing import ClassVar

from ..detection import ResultLibrary
from ..vocabulary import ClassListStore
from .result_archive import ResultArchive


class ResultStore:
    """
    Detection results remembered between runs as one ``ResultArchive``, ``results.ovdresults`` in a data directory.

    The directory is created only when written to.
    """

    FILE_NAME: ClassVar[str] = f"results{ResultArchive.SUFFIX}"

    def __init__(self, root_directory: Path) -> None:
        """
        Parameters
        ----------
        root_directory : Path
            Data directory holding the archive.
        """
        self._root_directory: Path = root_directory
        self._archive: ResultArchive = ResultArchive(root_directory / self.FILE_NAME)

    @classmethod
    def in_working_directory(cls) -> "ResultStore":
        """
        Build a store in the data directory under the current working directory.

        Returns
        -------
        ResultStore
            Store rooted at ``<cwd>/ovd_gui_data``.
        """
        return cls(Path.cwd() / ClassListStore.DEFAULT_DIRECTORY_NAME)

    @property
    def path(self) -> Path:
        """
        File holding the results.

        Returns
        -------
        Path
            ``results.ovdresults`` in the data directory, whether or not it exists.
        """
        return self._archive.path

    def load(self) -> ResultLibrary:
        """
        Read the remembered results.

        Returns
        -------
        ResultLibrary
            Stored results of unchanged image files; empty when nothing is stored.

        Raises
        ------
        OSError
            If the archive exists but cannot be read.
        ValueError
            If the archive content is invalid.
        """
        if not self.path.is_file():
            return ResultLibrary()
        return self._archive.read()

    def save(self, library: ResultLibrary) -> None:
        """
        Remember every result for the next run.

        Parameters
        ----------
        library : ResultLibrary
            Results to store.

        Raises
        ------
        OSError
            If the data directory or the archive cannot be written.
        """
        self._root_directory.mkdir(parents=True, exist_ok=True)
        self._archive.write(library)
