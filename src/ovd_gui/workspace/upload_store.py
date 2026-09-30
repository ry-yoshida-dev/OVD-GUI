import hashlib
from pathlib import Path
from typing import ClassVar


class UploadStore:
    """
    Default folder receiving the image files sent from a browser, which cannot tell the server where its files are.

    Uploaded files are kept under ``uploads`` in the data directory with the relative folder path they were dropped
    with, so that they can be opened, detected and remembered like any other image file. Sending the same file again
    reuses the stored copy, which keeps its results; a different file of the same name is stored under a numbered
    name instead of replacing the first one.
    """

    DIRECTORY_NAME: ClassVar[str] = "uploads"
    DEFAULT_DIRECTORY_NAME: ClassVar[str] = "ovd_gui_data"
    FALLBACK_FILE_NAME: ClassVar[str] = "upload"
    SKIPPED_PARTS: ClassVar[frozenset[str]] = frozenset({"", ".", ".."})

    def __init__(self, root_directory: Path) -> None:
        """
        Parameters
        ----------
        root_directory : Path
            Data directory holding the ``uploads`` folder.
        """
        self._directory: Path = root_directory / self.DIRECTORY_NAME

    @classmethod
    def in_working_directory(cls) -> "UploadStore":
        """
        Build a store in the data directory under the current working directory.

        Returns
        -------
        UploadStore
            Store writing to ``<cwd>/ovd_gui_data/uploads``.
        """
        return cls(Path.cwd() / cls.DEFAULT_DIRECTORY_NAME)

    @property
    def directory(self) -> Path:
        """
        Folder holding the uploaded files.

        Returns
        -------
        Path
            ``uploads`` under the data directory; created on the first upload.
        """
        return self._directory

    def save(self, relative_name: str, content: bytes) -> Path:
        """
        Store one uploaded file.

        Parameters
        ----------
        relative_name : str
            File name sent by the browser, possibly with the folders it was dropped in, separated by ``/`` or ``\\``.
            Parts leading outside the folder are dropped.
        content : bytes
            File content.

        Returns
        -------
        Path
            Stored file: an existing copy with the same content, or a new file.

        Raises
        ------
        OSError
            If the file cannot be written.
        """
        target: Path = self._directory.joinpath(*self._safe_parts(relative_name))
        digest: str = hashlib.sha256(content).hexdigest()
        candidate: Path = target
        copy_number: int = 0
        while candidate.exists():
            if candidate.is_file() and self._digest_of(candidate) == digest:
                return candidate
            copy_number += 1
            candidate = target.with_name(f"{target.stem}-{copy_number}{target.suffix}")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        partial: Path = candidate.with_name(f".{candidate.name}.partial")
        partial.write_bytes(content)
        partial.replace(candidate)
        return candidate

    def _safe_parts(self, relative_name: str) -> tuple[str, ...]:
        parts: tuple[str, ...] = tuple(
            part.strip()
            for part in relative_name.replace("\\", "/").split("/")
            if part.strip() not in self.SKIPPED_PARTS
        )
        return parts or (self.FALLBACK_FILE_NAME,)

    @staticmethod
    def _digest_of(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
