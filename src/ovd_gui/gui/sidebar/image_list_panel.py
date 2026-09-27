from collections.abc import Mapping
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem, QMenu, QWidget

from .image_count_delegate import ImageCountDelegate
from .image_state import ImageState
from .image_status import ImageStatus
from .status_dot_icon import StatusDotIcon


class ImageListPanel(QListWidget):
    """
    List of the open images, one row per file in the order they were added.

    Each row carries a dot telling whether the image is detected, outdated, failed or not analyzed yet with the
    shown model, and the number of its kept detections. Selected images can be closed from the right-click menu or
    with Delete; closing asks the window through ``removal_requested``, which then calls ``remove_images``.

    Signals
    -------
    current_image_changed : Signal()
        Another image, or no image, became current.
    removal_requested : Signal(tuple)
        The user asked to close the images of the tuple of paths.
    """

    current_image_changed: Signal = Signal()
    removal_requested: Signal = Signal(tuple)

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
        self._statuses: dict[Path, ImageStatus] = {}
        self._state_icons: dict[ImageState, QIcon] = {
            state: StatusDotIcon(state.color, state.is_marked_filled).to_icon() for state in ImageState
        }
        self._remove_action: QAction = QAction("Close Selected Images", self)
        self._remove_action.setShortcuts(
            [QKeySequence(QKeySequence.StandardKey.Delete), QKeySequence(Qt.Key.Key_Backspace)]
        )
        self._remove_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._remove_all_action: QAction = QAction("Close All Images", self)
        self.addAction(self._remove_action)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setItemDelegate(ImageCountDelegate(self))
        self.currentRowChanged.connect(self._on_current_row_changed)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._remove_action.triggered.connect(self._request_removal_of_selection)
        self._remove_all_action.triggered.connect(lambda: self.removal_requested.emit(tuple(self._image_paths)))

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
    def selected_paths(self) -> tuple[Path, ...]:
        """
        Images of the selected rows.

        Returns
        -------
        tuple[Path, ...]
            Selected images in list order.
        """
        selected_rows: set[int] = {self.row(item) for item in self.selectedItems()}
        return tuple(path for row, path in enumerate(self._image_paths) if row in selected_rows)

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
            self.addItem(item)
            self._decorate(item, path)
        if image_paths:
            self.setCurrentRow(first_new_row)

    def remove_images(self, image_paths: tuple[Path, ...]) -> None:
        """
        Close images; when the current image is closed, the next remaining one becomes current.

        Parameters
        ----------
        image_paths : tuple[Path, ...]
            Images to close; images not listed are ignored.
        """
        removed_paths: set[Path] = set(image_paths) & set(self._image_paths)
        if not removed_paths:
            return
        current_path: Path | None = self.current_path
        current_row: int = self.currentRow()
        self.blockSignals(True)
        for row in range(len(self._image_paths) - 1, -1, -1):
            if self._image_paths[row] in removed_paths:
                del self._image_paths[row]
                self.takeItem(row)
        for path in removed_paths:
            self._statuses.pop(path, None)
        if current_path in removed_paths or current_path is None:
            self.setCurrentRow(min(current_row, len(self._image_paths) - 1) if self._image_paths else -1)
        else:
            self.setCurrentRow(self._image_paths.index(current_path))
        self.blockSignals(False)
        if current_path in removed_paths:
            self.current_image_changed.emit()

    def set_statuses(self, statuses: Mapping[Path, ImageStatus]) -> None:
        """
        Mark each image with its state and kept detection count.

        Parameters
        ----------
        statuses : Mapping[Path, ImageStatus]
            Status of the listed images; images left out are marked not analyzed.
        """
        self._statuses = {path: status for path, status in statuses.items() if path in self._image_paths}
        for row, path in enumerate(self._image_paths):
            self._decorate(self.item(row), path)

    def status_of(self, image_path: Path) -> ImageStatus:
        """
        Status shown for one image.

        Parameters
        ----------
        image_path : Path
            Listed image.

        Returns
        -------
        ImageStatus
            Last status set, or not analyzed.
        """
        return self._statuses.get(image_path, ImageStatus(ImageState.NOT_ANALYZED))

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

    def select_neighbor(self, step: int) -> bool:
        """
        Make the image before or after the current one current.

        Parameters
        ----------
        step : int
            -1 for the previous image, 1 for the next one; other offsets move further.

        Returns
        -------
        bool
            False when no image lies there.
        """
        target_row: int = self.currentRow() + step if self.currentRow() >= 0 else 0
        if not self._image_paths or not 0 <= target_row < len(self._image_paths):
            return False
        self.setCurrentRow(target_row)
        return True

    def _decorate(self, item: QListWidgetItem, path: Path) -> None:
        status: ImageStatus = self.status_of(path)
        item.setIcon(self._state_icons[status.state])
        item.setData(ImageCountDelegate.COUNT_ROLE, status.count_text)
        item.setToolTip(f"{path}\n{status.description}")

    def _on_current_row_changed(self, row: int) -> None:
        self.current_image_changed.emit()

    def _request_removal_of_selection(self) -> None:
        selected_paths: tuple[Path, ...] = self.selected_paths
        if selected_paths:
            self.removal_requested.emit(selected_paths)

    def _show_context_menu(self, position: QPoint) -> None:
        if not self._image_paths:
            return
        selected_count: int = len(self.selected_paths)
        self._remove_action.setText(
            f"Close {selected_count} Selected Images" if selected_count > 1 else "Close Selected Image"
        )
        self._remove_action.setEnabled(selected_count > 0)
        menu: QMenu = QMenu(self)
        menu.addAction(self._remove_action)
        menu.addAction(self._remove_all_action)
        menu.exec(self.viewport().mapToGlobal(position))
