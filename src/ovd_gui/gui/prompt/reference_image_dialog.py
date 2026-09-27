from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...detection import ReferenceBox, ReferenceImage
from ...media import LoadedImage
from ..class_palette import ClassPalette
from ..viewer import ImageCanvas


class ReferenceImageDialog(QDialog):
    """
    Modal dialog marking the examples of one class on a reference image.

    Dragging draws boxes around examples; a drawn box is moved by dragging inside it and resized by its round corner
    handles. Accepting without any box uses the whole image, which suits an image already cropped to the example.
    Reference images are separate from the images to analyze.
    """

    WINDOW_TITLE = "Reference Image"
    MINIMUM_WIDTH = 640
    MINIMUM_HEIGHT = 480

    def __init__(self, palette: ClassPalette, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        palette : ClassPalette
            Colors of the classes.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(self.MINIMUM_WIDTH, self.MINIMUM_HEIGHT)
        self._loaded_image: LoadedImage | None = None
        self._reference_image: ReferenceImage | None = None
        self._class_name: str = ""
        self._class_names: tuple[str, ...] = ()
        self._boxes: list[ReferenceBox] = []

        self._instruction_label: QLabel = QLabel()
        self._instruction_label.setWordWrap(True)
        self._canvas: ImageCanvas = ImageCanvas(palette)
        self._canvas.setAcceptDrops(False)
        self._canvas.set_drawing_enabled(True)
        self._canvas.rectangle_drawn.connect(self._on_rectangle_drawn)
        self._canvas.reference_adjusted.connect(self._on_reference_adjusted)

        self._undo_button: QPushButton = QPushButton("Undo Box")
        self._undo_button.clicked.connect(self._undo_box)
        self._clear_button: QPushButton = QPushButton("Clear Boxes")
        self._clear_button.clicked.connect(self._clear_boxes)
        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button: QPushButton = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        footer: QHBoxLayout = QHBoxLayout()
        footer.addWidget(self._undo_button)
        footer.addWidget(self._clear_button)
        footer.addStretch(1)
        footer.addWidget(self._button_box)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.addWidget(self._instruction_label)
        layout.addWidget(self._canvas, stretch=1)
        layout.addLayout(footer)

    @property
    def boxes(self) -> tuple[ReferenceBox, ...]:
        """
        Reference boxes the dialog currently yields.

        Returns
        -------
        tuple[ReferenceBox, ...]
            Drawn boxes, or one box covering the whole image while none is drawn; empty before an image is set.
        """
        if self._loaded_image is None or self._reference_image is None:
            return ()
        if self._boxes:
            return tuple(self._boxes)
        width, height = self._loaded_image.image.size
        return (
            ReferenceBox(
                reference_image=self._reference_image,
                class_name=self._class_name,
                left=0.0,
                top=0.0,
                right=float(width),
                bottom=float(height),
            ),
        )

    def set_reference_image(self, loaded_image: LoadedImage, class_name: str, class_names: tuple[str, ...]) -> None:
        """
        Show a reference image with no box drawn yet.

        Parameters
        ----------
        loaded_image : LoadedImage
            Reference image.
        class_name : str
            Class the examples on the image belong to.
        class_names : tuple[str, ...]
            Current classes, whose index selects the box color.
        """
        self._loaded_image = loaded_image
        self._reference_image = ReferenceImage.of(loaded_image.path.name, loaded_image.image)
        self._class_name = class_name
        self._class_names = class_names
        self._boxes = []
        self.setWindowTitle(f"{self.WINDOW_TITLE}: {class_name} · {loaded_image.path.name}")
        self._instruction_label.setText(
            f"Drag boxes around examples of '{class_name}'; drag a box to move it or its corners to resize it. "
            + "Without a box the whole image is used as the example."
        )
        self._canvas.set_image(loaded_image.image)
        self._show_boxes()

    def ask(
        self, loaded_image: LoadedImage, class_name: str, class_names: tuple[str, ...]
    ) -> tuple[ReferenceBox, ...] | None:
        """
        Run the dialog on one reference image.

        Parameters
        ----------
        loaded_image : LoadedImage
            Reference image.
        class_name : str
            Class the examples on the image belong to.
        class_names : tuple[str, ...]
            Current classes, whose index selects the box color.

        Returns
        -------
        tuple[ReferenceBox, ...] | None
            Boxes to add, or ``None`` if the user cancelled.
        """
        self.set_reference_image(loaded_image, class_name, class_names)
        if self.exec() != QDialog.DialogCode.Accepted:
            return None
        return self.boxes

    def _on_rectangle_drawn(self, rectangle: QRectF) -> None:
        if self._reference_image is None:
            return
        self._boxes.append(
            ReferenceBox(
                reference_image=self._reference_image,
                class_name=self._class_name,
                left=rectangle.left(),
                top=rectangle.top(),
                right=rectangle.right(),
                bottom=rectangle.bottom(),
            )
        )
        self._show_boxes()

    def _on_reference_adjusted(self, box_index: int, rectangle: QRectF) -> None:
        if not 0 <= box_index < len(self._boxes):
            return
        self._boxes[box_index] = ReferenceBox(
            reference_image=self._boxes[box_index].reference_image,
            class_name=self._boxes[box_index].class_name,
            left=rectangle.left(),
            top=rectangle.top(),
            right=rectangle.right(),
            bottom=rectangle.bottom(),
        )
        self._show_boxes()

    def _undo_box(self) -> None:
        if self._boxes:
            self._boxes.pop()
            self._show_boxes()

    def _clear_boxes(self) -> None:
        self._boxes = []
        self._show_boxes()

    def _show_boxes(self) -> None:
        self._canvas.show_references(self._boxes, self._class_names)
        is_drawn: bool = bool(self._boxes)
        self._undo_button.setEnabled(is_drawn)
        self._clear_button.setEnabled(is_drawn)
        self._ok_button.setText(
            f"Add {len(self._boxes)} Box{'' if len(self._boxes) == 1 else 'es'}" if is_drawn else "Use Whole Image"
        )
