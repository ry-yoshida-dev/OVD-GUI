from collections.abc import Iterable
from pathlib import Path

from .class_definition import ClassDefinition


class ClassListFile:
    """
    Plain-text class list with one class per line.

    A line is a class name, as in YOLO ``classes.txt`` or Darknet ``.names`` files, or a class name followed by its
    phrases, ``car: car, suv, taxi``. Classes queried by their name only are written as plain names, so such lists
    stay readable by other tools. Blank lines are skipped when reading.
    """

    SUFFIXES: tuple[str, ...] = (".txt", ".names")
    ENCODING = "utf-8"

    def __init__(self, path: Path) -> None:
        """
        Parameters
        ----------
        path : Path
            Location of the file.
        """
        self._path: Path = path

    @property
    def path(self) -> Path:
        """
        Location of the file.

        Returns
        -------
        Path
            Path given at construction.
        """
        return self._path

    def read(self) -> tuple[ClassDefinition, ...]:
        """
        Read the classes.

        Returns
        -------
        tuple[ClassDefinition, ...]
            One class per non-blank line, in file order.

        Raises
        ------
        OSError
            If the file cannot be read.
        UnicodeDecodeError
            If the file is not UTF-8 text.
        ValueError
            If a line is not a valid class.
        """
        lines: list[str] = self._path.read_text(encoding=self.ENCODING).splitlines()
        return tuple(ClassDefinition.parse(line) for line in lines if line.strip())

    def write(self, definitions: Iterable[ClassDefinition]) -> None:
        """
        Write the classes, replacing the file.

        Parameters
        ----------
        definitions : Iterable[ClassDefinition]
            Classes in class id order.

        Raises
        ------
        OSError
            If the file cannot be written.
        """
        self._path.write_text("".join(f"{definition.text}\n" for definition in definitions), encoding=self.ENCODING)
