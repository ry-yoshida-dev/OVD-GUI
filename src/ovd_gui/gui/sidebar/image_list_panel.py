from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget


class ImageListPanel(QListWidget):
    """
    List of the open images, one row per file in the order they were added.

    Signals
    -------
    current_image_changed : Signal()
        Another image, or no image, became current.
    """

    current_image_changed: Signal = Signal()

    TITLE = "Images"

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._image_paths: list[Path] = []
        self.currentRowChanged.connect(self._on_current_row_changed)

    @property
    def image_paths(self) -> tuple[Path, ...]:
        """
        Open images in list order.

        Returns
        -------
        tuple[Path, ...]
            Resolved image files.
        """
        return tuple(self._image_paths)

    @property
    def current_path(self) -> Path | None:
        """
        Image of the current row.

        Returns
        -------
        Path | None
            ``None`` while no row is current.
        """
        row: int = self.currentRow()
        return self._image_paths[row] if 0 <= row < len(self._image_paths) else None

    @property
    def title(self) -> str:
        """
        Section title with the number of open images.

        Returns
        -------
        str
            ``"Images"``, or ``"Images (n)"`` once images are open.
        """
        return f"{self.TITLE} ({len(self._image_paths)})" if self._image_paths else self.TITLE

    def add_images(self, image_paths: tuple[Path, ...]) -> None:
        """
        Append images and make the first of them current.

        Parameters
        ----------
        image_paths : tuple[Path, ...]
            Resolved image files not listed yet.

        Raises
        ------
        ValueError
            If an image is already listed.
        """
        if any(path in self._image_paths for path in image_paths):
            raise ValueError("An image is already listed.")
        first_new_row: int = len(self._image_paths)
        for path in image_paths:
            self._image_paths.append(path)
            item: QListWidgetItem = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            self.addItem(item)
        if image_paths:
            self.setCurrentRow(first_new_row)

    def select(self, image_path: Path) -> bool:
        """
        Make a listed image current.

        Parameters
        ----------
        image_path : Path
            Image to show.

        Returns
        -------
        bool
            False when the image is not listed.
        """
        if image_path not in self._image_paths:
            return False
        self.setCurrentRow(self._image_paths.index(image_path))
        return True

    def _on_current_row_changed(self, row: int) -> None:
        self.current_image_changed.emit()
