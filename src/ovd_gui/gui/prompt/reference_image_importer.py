from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from ...detection import ReferenceBoard, ReferenceBox
from ...media import LoadedImage
from ..class_palette import ClassPalette
from .reference_image_dialog import ReferenceImageDialog


class ReferenceImageImporter:
    """
    Interactive addition of reference images to a class: pick image files, then box the examples of each one.

    Each accepted image adds its boxes to the reference board; cancelling the box dialog stops before the remaining
    files. The directory of the last pick is offered again next time.
    """

    def __init__(self, palette: ClassPalette, reference_board: ReferenceBoard, parent: QWidget) -> None:
        """
        Parameters
        ----------
        palette : ClassPalette
            Colors of the boxes in the dialog.
        reference_board : ReferenceBoard
            Board receiving the boxes.
        parent : QWidget
            Parent of the file and box dialogs.
        """
        self._board: ReferenceBoard = reference_board
        self._parent: QWidget = parent
        self._dialog: ReferenceImageDialog = ReferenceImageDialog(palette, parent)
        self._last_directory: Path = Path.cwd()

    def import_images(self, class_name: str, class_names: tuple[str, ...]) -> int:
        """
        Ask for reference images of a class and add their boxes to the board.

        Parameters
        ----------
        class_name : str
            Class the examples show.
        class_names : tuple[str, ...]
            Every class, to label the boxes already on the board.

        Returns
        -------
        int
            Number of images added.
        """
        file_names, _ = QFileDialog.getOpenFileNames(
            self._parent,
            f"Reference Images of '{class_name}'",
            str(self._last_directory),
            f"Images ({LoadedImage.suffix_patterns()})",
        )
        if not file_names:
            return 0
        self._last_directory = Path(file_names[0]).parent
        added_image_count: int = 0
        for file_name in file_names:
            path: Path = Path(file_name)
            try:
                reference_image: LoadedImage = LoadedImage.open(path)
            except OSError as error:
                QMessageBox.warning(self._parent, "Cannot open image", f"{path}\n{error}")
                continue
            boxes: tuple[ReferenceBox, ...] | None = self._dialog.ask(reference_image, class_name, class_names)
            if boxes is None:
                break
            for box in boxes:
                self._board.add(box, reference_image.image)
            added_image_count += 1
        return added_image_count
