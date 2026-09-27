from pathlib import Path

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QResizeEvent
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QMessageBox, QVBoxLayout, QWidget

from ...media import ImageCollection, LoadedImage
from ..intake import DropOverlay, DropZone


class ReferenceSourceDialog(QDialog):
    """
    Modal dialog choosing the reference images of a class.

    Images and folders are dropped onto it, or picked with its open buttons; a folder contributes the images directly
    inside it. The directory of the last pick is offered again next time.
    """

    MINIMUM_WIDTH = 520
    MINIMUM_HEIGHT = 380

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self.setMinimumSize(self.MINIMUM_WIDTH, self.MINIMUM_HEIGHT)
        self.setAcceptDrops(True)
        self._image_paths: tuple[Path, ...] = ()
        self._last_directory: Path = Path.cwd()
        self._is_drop_acceptable: bool = False

        self._drop_zone: DropZone = DropZone("Drop reference images or folders here")
        self._drop_zone.open_images_requested.connect(self._choose_images)
        self._drop_zone.open_folder_requested.connect(self._choose_folder)
        button_box: QDialogButtonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.rejected.connect(self.reject)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.addWidget(self._drop_zone, stretch=1)
        layout.addWidget(button_box)
        self._drop_overlay: DropOverlay = DropOverlay(self)

    @property
    def image_paths(self) -> tuple[Path, ...]:
        """
        Reference images chosen by the last accepted pick or drop.

        Returns
        -------
        tuple[Path, ...]
            Resolved image files in the order given; directory contents are sorted by name.
        """
        return self._image_paths

    def ask(self, class_name: str) -> tuple[Path, ...]:
        """
        Run the dialog for one class.

        Parameters
        ----------
        class_name : str
            Class the reference images show.

        Returns
        -------
        tuple[Path, ...]
            Chosen image files, empty if the user cancelled.
        """
        self._image_paths = ()
        self.setWindowTitle(f"Reference Images of '{class_name}'")
        if self.exec() != QDialog.DialogCode.Accepted:
            return ()
        return self._image_paths

    def take_paths(self, candidate_paths: list[Path]) -> bool:
        """
        Accept the images found in files and folders, as a drop or a pick does.

        Parameters
        ----------
        candidate_paths : list[Path]
            Files and directories given by the user.

        Returns
        -------
        bool
            True if any supported image was found and the dialog was accepted.
        """
        collection: ImageCollection = ImageCollection.gather(candidate_paths, ())
        if collection.is_empty:
            return False
        self._image_paths = collection.image_paths
        self._last_directory = collection.image_paths[0].parent
        self.accept()
        return True

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        dropped_paths: list[Path] = self._local_paths_of(event.mimeData())
        if not dropped_paths:
            event.ignore()
            return
        collection: ImageCollection = ImageCollection.gather(dropped_paths, ())
        self._is_drop_acceptable = not collection.is_empty
        self._drop_overlay.present(collection, self.rect())
        event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if self._is_drop_acceptable:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._drop_overlay.hide()

    def dropEvent(self, event: QDropEvent) -> None:
        self._drop_overlay.hide()
        event.acceptProposedAction()
        self.take_paths(self._local_paths_of(event.mimeData()))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._drop_overlay.setGeometry(self.rect())

    @staticmethod
    def _local_paths_of(mime_data: QMimeData) -> list[Path]:
        return [Path(url.toLocalFile()) for url in mime_data.urls() if url.isLocalFile()]

    def _choose_images(self) -> None:
        file_names, _ = QFileDialog.getOpenFileNames(
            self, self.windowTitle(), str(self._last_directory), f"Images ({LoadedImage.suffix_patterns()})"
        )
        if file_names:
            self.take_paths([Path(file_name) for file_name in file_names])

    def _choose_folder(self) -> None:
        directory: str = QFileDialog.getExistingDirectory(self, self.windowTitle(), str(self._last_directory))
        if not directory:
            return
        if not self.take_paths([Path(directory)]):
            QMessageBox.information(self, "No supported images", f"{directory}\n{LoadedImage.supported_format_label()}")
