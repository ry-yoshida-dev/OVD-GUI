from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...storage import ClassSet, ClassSetArchive, ClassSetEntry, ClassSetStore
from ..class_palette import ClassPalette
from .class_set_preview import ClassSetPreview
from .class_set_row_delegate import ClassSetRowDelegate
from .trash_icon import TrashIcon


class ClassSetDialog(QDialog):
    """
    Library of the saved class sets: browse, preview, load, rename, delete, import and export them.

    The list on the left is filtered by the search field, matching set and class names; the preview on the right
    shows the classes, text prompts and image prompts of the selected set. ``Load`` (or a double-click or Enter)
    closes the dialog with the set to load. A set is renamed in place (F2) and deleted after a confirmation
    (Delete). Sets whose file cannot be read are still listed, so they can be deleted.
    """

    WINDOW_TITLE = "Class Sets"
    MINIMUM_WIDTH = 780
    MINIMUM_HEIGHT = 500
    LIST_WIDTH = 270
    NAME_ROLE = Qt.ItemDataRole.UserRole
    LIST_INDEX = 0
    EMPTY_INDEX = 1

    def __init__(self, class_set_store: ClassSetStore, palette: ClassPalette, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        class_set_store : ClassSetStore
            Data directory holding the class sets.
        palette : ClassPalette
            Colors of the classes in the preview.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(self.MINIMUM_WIDTH, self.MINIMUM_HEIGHT)
        self._store: ClassSetStore = class_set_store
        self._entries: dict[str, ClassSetEntry] = {}
        self._loaded_sets: dict[tuple[str, datetime], ClassSet] = {}
        self._chosen_name: str | None = None
        self._renamed_names: dict[str, str] = {}
        self._last_directory: Path = Path.home()
        self._is_populating: bool = False

        self._search_edit: QLineEdit = QLineEdit()
        self._search_edit.setPlaceholderText("Search sets and classes")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._apply_filter)

        self._list: QListWidget = QListWidget()
        self._list.setItemDelegate(ClassSetRowDelegate(self._list))
        self._list.setMouseTracking(True)
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        self._list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list.setEditTriggers(
            QAbstractItemView.EditTrigger.EditKeyPressed | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.currentItemChanged.connect(self._on_current_item_changed)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.itemChanged.connect(self._on_item_renamed)
        self._list.setAutoFillBackground(False)
        self._list.viewport().setAutoFillBackground(False)

        self._empty_label: QLabel = QLabel()
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        self._empty_label.setContentsMargins(16, 16, 16, 16)
        self._list_stack: QStackedWidget = QStackedWidget()
        self._list_stack.insertWidget(self.LIST_INDEX, self._list)
        self._list_stack.insertWidget(self.EMPTY_INDEX, self._empty_label)

        self._rename_action: QAction = self._create_action("Rename", self._rename_current, QKeySequence(Qt.Key.Key_F2))
        self._delete_action: QAction = self._create_action(
            "Delete…", self._delete_current, QKeySequence(QKeySequence.StandardKey.Delete)
        )
        self._delete_action.setIcon(TrashIcon(self.palette().color(QPalette.ColorRole.ButtonText)).to_icon())
        self._export_action: QAction = self._create_action("Export…", self._export_current)
        self._import_action: QAction = self._create_action("Import…", self._import_archive)
        self._load_action: QAction = self._create_action("Load", self._load_current)

        list_footer: QHBoxLayout = QHBoxLayout()
        list_footer.setContentsMargins(4, 4, 4, 0)
        list_footer.setSpacing(2)
        list_footer.addWidget(self._tool_button_of(self._import_action))
        list_footer.addWidget(self._tool_button_of(self._export_action))
        list_footer.addStretch(1)
        list_footer.addWidget(self._tool_button_of(self._rename_action))
        delete_button: QToolButton = self._tool_button_of(self._delete_action)
        delete_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        delete_button.setToolTip("Delete the selected class set (Delete)")
        list_footer.addWidget(delete_button)

        list_pane: QWidget = QWidget()
        list_layout: QVBoxLayout = QVBoxLayout(list_pane)
        list_layout.setContentsMargins(0, 0, 8, 0)
        list_layout.setSpacing(6)
        list_layout.addWidget(self._search_edit)
        list_layout.addWidget(self._list_stack, stretch=1)
        list_layout.addLayout(list_footer)

        self._preview: ClassSetPreview = ClassSetPreview(palette)
        preview_frame: QFrame = QFrame()
        preview_frame.setFrameShape(QFrame.Shape.StyledPanel)
        preview_frame.setAutoFillBackground(True)
        preview_frame.setBackgroundRole(QPalette.ColorRole.Base)
        preview_layout: QVBoxLayout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(self._preview)

        splitter: QSplitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(list_pane)
        splitter.addWidget(preview_frame)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([self.LIST_WIDTH, self.MINIMUM_WIDTH - self.LIST_WIDTH])

        close_button: QPushButton = QPushButton("Close")
        close_button.setAutoDefault(False)
        close_button.clicked.connect(self.reject)
        self._load_button: QPushButton = QPushButton("Load")
        self._load_button.setDefault(True)
        self._load_button.setToolTip("Replace the current classes and reference images with the selected set")
        self._load_button.clicked.connect(self._load_current)
        footer: QHBoxLayout = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close_button)
        footer.addWidget(self._load_button)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(12)
        layout.addWidget(splitter, stretch=1)
        layout.addLayout(footer)

    @property
    def listed_names(self) -> tuple[str, ...]:
        """
        Names of the class sets currently visible in the list.

        Returns
        -------
        tuple[str, ...]
            Names in list order, leaving out rows hidden by the search.
        """
        return tuple(
            str(item.data(self.NAME_ROLE))
            for item in (self._list.item(row) for row in range(self._list.count()))
            if not item.isHidden()
        )

    @property
    def current_name(self) -> str | None:
        """
        Class set of the current row.

        Returns
        -------
        str | None
            ``None`` while no row is current.
        """
        item: QListWidgetItem | None = self._current_item()
        return None if item is None else str(item.data(self.NAME_ROLE))

    @property
    def chosen_name(self) -> str | None:
        """
        Class set chosen with ``Load``.

        Returns
        -------
        str | None
            ``None`` until a set is loaded from the dialog.
        """
        return self._chosen_name

    @property
    def preview(self) -> ClassSetPreview:
        """
        Preview of the current class set.

        Returns
        -------
        ClassSetPreview
            Widget on the right side.
        """
        return self._preview

    def ask(self, current_name: str) -> str | None:
        """
        Run the dialog.

        Parameters
        ----------
        current_name : str
            Class set loaded or saved last, selected when the dialog opens; empty for none.

        Returns
        -------
        str | None
            Name of the set to load, or ``None`` if the dialog was closed without loading.
        """
        self.open_library(current_name)
        if self.exec() != QDialog.DialogCode.Accepted:
            return None
        return self._chosen_name

    def open_library(self, current_name: str) -> None:
        """
        List the saved class sets and select one, without running the dialog.

        Parameters
        ----------
        current_name : str
            Set to select; the first set is selected when it is not listed.
        """
        self._chosen_name = None
        self._renamed_names = {}
        self._search_edit.clear()
        self._populate(current_name)
        self._list.setFocus()

    def delete_class_set(self, name: str) -> None:
        """
        Delete a class set without asking, and list the remaining sets.

        Parameters
        ----------
        name : str
            Class set name.

        Raises
        ------
        ValueError
            If the name is not usable as a file name.
        OSError
            If the file cannot be deleted.
        """
        row: int = self._row_of(name)
        self._store.delete_class_set(name)
        remaining_names: tuple[str, ...] = tuple(entry_name for entry_name in self._entries if entry_name != name)
        next_name: str = remaining_names[min(row, len(remaining_names) - 1)] if remaining_names else ""
        self._populate(next_name)

    def rename_class_set(self, name: str, new_name: str) -> None:
        """
        Rename a class set and keep it selected.

        Parameters
        ----------
        name : str
            Current class set name.
        new_name : str
            New class set name.

        Raises
        ------
        ValueError
            If a name is not usable as a file name.
        FileExistsError
            If another set already has the new name.
        OSError
            If the file cannot be renamed.
        """
        self._store.rename_class_set(name, new_name)
        self._renamed_names = {
            original: new_name.strip() if renamed == name else renamed
            for original, renamed in self._renamed_names.items()
        }
        self._renamed_names.setdefault(name, new_name.strip())
        self._populate(new_name.strip())

    def name_after_renames(self, name: str) -> str:
        """
        Current name of a class set renamed since the library was last opened.

        Parameters
        ----------
        name : str
            Name of the set when the library was opened.

        Returns
        -------
        str
            Its current name; ``name`` itself when it was not renamed.
        """
        return self._renamed_names.get(name, name)

    def _populate(self, selected_name: str) -> None:
        self._is_populating = True
        self._list.clear()
        self._entries = {entry.name: entry for entry in self._store.entries}
        now: datetime = datetime.now().astimezone()
        for entry in self._entries.values():
            item: QListWidgetItem = QListWidgetItem(entry.name)
            item.setData(self.NAME_ROLE, entry.name)
            item.setData(ClassSetRowDelegate.SAVED_AT_ROLE, self._saved_at_text(entry.saved_at, now))
            item.setData(
                ClassSetRowDelegate.DETAIL_ROLE,
                entry.summary.description if entry.summary is not None else "Cannot be read — delete or replace it",
            )
            item.setData(ClassSetRowDelegate.IS_READABLE_ROLE, entry.is_readable)
            item.setToolTip(
                ", ".join(entry.summary.class_names)
                if entry.summary is not None
                else str(self._store.path_of(entry.name))
            )
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self._list.addItem(item)
        self._is_populating = False
        self._apply_filter(self._search_edit.text())
        names: tuple[str, ...] = self.listed_names
        if names:
            self._list.setCurrentRow(self._row_of(selected_name if selected_name in names else names[0]))
        self._on_current_item_changed(self._current_item(), None)

    def _apply_filter(self, text: str) -> None:
        needle: str = text.strip().casefold()
        for row in range(self._list.count()):
            item: QListWidgetItem = self._list.item(row)
            entry: ClassSetEntry = self._entries[str(item.data(self.NAME_ROLE))]
            haystack: list[str] = [entry.name, *(entry.summary.class_names if entry.summary is not None else ())]
            item.setHidden(bool(needle) and not any(needle in candidate.casefold() for candidate in haystack))
        if not self._entries:
            self._empty_label.setText(
                "No class sets yet.\n\nSave the current classes with ⋯ › Save Class Set..., or import a .ovdset file."
            )
        elif not self.listed_names:
            self._empty_label.setText(f"No class set matches “{text.strip()}”.")
        self._list_stack.setCurrentIndex(self.LIST_INDEX if self.listed_names else self.EMPTY_INDEX)
        current_item: QListWidgetItem | None = self._current_item()
        if current_item is not None and current_item.isHidden() and self.listed_names:
            self._list.setCurrentRow(self._row_of(self.listed_names[0]))
        self._update_actions()

    def _on_current_item_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        self._update_actions()
        if current is None or current.isHidden():
            self._preview.show_notice(
                "Select a class set to see its classes and image prompts." if self._entries else ""
            )
            return
        entry: ClassSetEntry = self._entries[str(current.data(self.NAME_ROLE))]
        if not entry.is_readable:
            self._preview.show_notice(
                f"“{entry.name}” cannot be read as a class set.\nDelete it, or replace it by saving or importing a set "
                + "of the same name.",
                is_warning=True,
            )
            return
        class_set: ClassSet | None = self._loaded_set_of(entry)
        if class_set is not None:
            self._preview.show_class_set(entry, class_set, str(current.data(ClassSetRowDelegate.SAVED_AT_ROLE)))

    def _loaded_set_of(self, entry: ClassSetEntry) -> ClassSet | None:
        key: tuple[str, datetime] = (entry.name, entry.saved_at)
        if key not in self._loaded_sets:
            try:
                self._loaded_sets[key] = self._store.read_class_set(entry.name)
            except (OSError, ValueError) as error:
                self._preview.show_notice(f"“{entry.name}” cannot be read.\n{error}", is_warning=True)
                return None
        return self._loaded_sets[key]

    def _update_actions(self) -> None:
        item: QListWidgetItem | None = self._current_item()
        is_selected: bool = item is not None and not item.isHidden()
        is_readable: bool = is_selected and item is not None and bool(item.data(ClassSetRowDelegate.IS_READABLE_ROLE))
        for action in (self._rename_action, self._delete_action):
            action.setEnabled(is_selected)
        for action in (self._export_action, self._load_action):
            action.setEnabled(is_readable)
        self._load_button.setEnabled(is_readable)

    def _load_current(self) -> None:
        name: str | None = self.current_name
        if name is None or not self._load_action.isEnabled():
            return
        self._chosen_name = name
        self.accept()

    def _rename_current(self) -> None:
        item: QListWidgetItem | None = self._current_item()
        if item is not None and not item.isHidden():
            self._list.editItem(item)

    def _on_item_renamed(self, item: QListWidgetItem) -> None:
        if self._is_populating:
            return
        name: str = str(item.data(self.NAME_ROLE))
        new_name: str = item.text().strip()
        if not new_name or new_name == name:
            self._revert_name(item, name)
            return
        try:
            self.rename_class_set(name, new_name)
        except (OSError, ValueError) as error:
            self._revert_name(item, name)
            QMessageBox.warning(self, "Cannot rename class set", str(error))

    def _revert_name(self, item: QListWidgetItem, name: str) -> None:
        self._is_populating = True
        item.setText(name)
        self._is_populating = False

    def _delete_current(self) -> None:
        name: str | None = self.current_name
        if name is None:
            return
        confirmation: QMessageBox = QMessageBox(
            QMessageBox.Icon.Warning,
            "Delete Class Set",
            f"Delete the class set “{name}”?",
            QMessageBox.StandardButton.NoButton,
            self,
        )
        confirmation.setInformativeText("Its classes, text prompts and reference images are removed from disk.")
        delete_button: QPushButton = confirmation.addButton("Delete", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button: QPushButton = confirmation.addButton(QMessageBox.StandardButton.Cancel)
        confirmation.setDefaultButton(cancel_button)
        confirmation.exec()
        if confirmation.clickedButton() is not delete_button:
            return
        try:
            self.delete_class_set(name)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot delete class set", str(error))

    def _import_archive(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import Class Set", str(self._last_directory), f"Class sets (*{ClassSetArchive.SUFFIX})"
        )
        if not file_name:
            return
        source_path: Path = Path(file_name)
        self._last_directory = source_path.parent
        name: str = source_path.stem
        try:
            if (
                self._store.has_class_set(name)
                and QMessageBox.question(self, "Import Class Set", f"Replace the class set “{name}”?")
                != QMessageBox.StandardButton.Yes
            ):
                return
            self._store.import_archive(source_path, name)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot import class set", f"{source_path}\n{error}")
            return
        self._search_edit.clear()
        self._populate(name)

    def _export_current(self) -> None:
        name: str | None = self.current_name
        if name is None:
            return
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export Class Set",
            str(self._last_directory / f"{name}{ClassSetArchive.SUFFIX}"),
            f"Class sets (*{ClassSetArchive.SUFFIX})",
        )
        if not file_name:
            return
        target_path: Path = Path(file_name)
        if not ClassSetArchive.is_archive_path(target_path):
            target_path = target_path.with_name(target_path.name + ClassSetArchive.SUFFIX)
        self._last_directory = target_path.parent
        try:
            self._store.export_archive(name, target_path)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot export class set", f"{target_path}\n{error}")

    def _show_context_menu(self, position: QPoint) -> None:
        if self._list.itemAt(position) is None:
            return
        context_menu: QMenu = QMenu(self)
        context_menu.addAction(self._load_action)
        context_menu.addSeparator()
        context_menu.addAction(self._rename_action)
        context_menu.addAction(self._export_action)
        context_menu.addSeparator()
        context_menu.addAction(self._delete_action)
        context_menu.exec(self._list.viewport().mapToGlobal(position))

    def _create_action(self, text: str, slot: Callable[[], None], shortcut: QKeySequence | None = None) -> QAction:
        action: QAction = QAction(text, self)
        action.triggered.connect(lambda: slot())
        if shortcut is not None:
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            self._list.addAction(action)
        return action

    @staticmethod
    def _tool_button_of(action: QAction) -> QToolButton:
        tool_button: QToolButton = QToolButton()
        tool_button.setDefaultAction(action)
        tool_button.setAutoRaise(True)
        tool_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        return tool_button

    def _current_item(self) -> QListWidgetItem | None:
        row: int = self._list.currentRow()
        return self._list.item(row) if row >= 0 else None

    def _on_item_double_clicked(self, _item: QListWidgetItem) -> None:
        self._load_current()

    def _row_of(self, name: str) -> int:
        for row in range(self._list.count()):
            if str(self._list.item(row).data(self.NAME_ROLE)) == name:
                return row
        return -1

    @staticmethod
    def _saved_at_text(saved_at: datetime, now: datetime) -> str:
        if saved_at.date() == now.date():
            return f"Today {saved_at:%H:%M}"
        if saved_at.date() == (now - timedelta(days=1)).date():
            return f"Yesterday {saved_at:%H:%M}"
        if saved_at.year == now.year:
            return f"{saved_at:%b} {saved_at.day}"
        return f"{saved_at:%b} {saved_at.day}, {saved_at.year}"
