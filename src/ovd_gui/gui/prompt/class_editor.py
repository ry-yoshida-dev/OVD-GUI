from collections.abc import Callable, Iterable
from functools import partial
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QPalette
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...detection import ReferenceBoard
from ...vocabulary import ClassDefinition, ClassListFile, ClassListStore, ClassVocabulary
from ..class_palette import ClassPalette
from .class_tree import ClassTree
from .reference_image_importer import ReferenceImageImporter
from .trash_icon import TrashIcon


class ClassEditor(QWidget):
    """
    Editor of the classes to detect and their queries: a ``ClassTree`` under a toolbar, as in a file explorer.

    ``+ Text`` inserts an empty row next to the selection, at the same level: a class after a selected class, a phrase
    after a selected phrase or reference image, a class at the end when nothing is selected. The new row is named in
    place and confirmed with Enter, so classes and phrases grow the same way. ``+ Image`` adds reference images to
    the current class (only while the backend takes image prompts), and the trash button or Delete removes the selected classes,
    phrases or images. Queries are moved between classes, or turned into classes, by dragging them. The context menu
    of the tree offers ``New Class`` and ``New Phrase`` explicitly, besides the image and remove actions.

    The ``⋯`` menu holds the class sets: ``Save...`` asks only for a name and stores the classes and phrases in the
    data directory, ``Load`` replaces them with a saved class set or any class list text file, and ``Clear`` removes
    every class. The classes are also remembered in the data directory after every change, to be restored at the next
    start. Reference images are kept for the session only.

    Signals
    -------
    classes_changed : Signal()
        A class, phrase or reference image was added, renamed or removed.
    message_posted : Signal(str)
        A short notice for the status bar, e.g. that a class set was saved or an entry was rejected.
    """

    classes_changed: Signal = Signal()
    message_posted: Signal = Signal(str)

    FILE_FILTER: str = (
        "Class lists (" + " ".join(f"*{suffix}" for suffix in ClassListFile.SUFFIXES) + ");;All files (*)"
    )

    def __init__(
        self,
        palette: ClassPalette,
        class_list_store: ClassListStore,
        reference_board: ReferenceBoard,
        parent: QWidget | None = None,
    ) -> None:
        """
        Parameters
        ----------
        palette : ClassPalette
            Colors of the classes.
        class_list_store : ClassListStore
            Data directory remembering the classes and holding the saved class sets.
        reference_board : ReferenceBoard
            Reference boxes shown under their classes; kept in step with renamed and removed classes.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._vocabulary: ClassVocabulary = ClassVocabulary()
        self._board: ReferenceBoard = reference_board
        self._class_list_store: ClassListStore = class_list_store
        self._class_set_name: str = ""
        self._last_directory: Path = class_list_store.class_set_directory
        self._reference_importer: ReferenceImageImporter = ReferenceImageImporter(palette, reference_board, self)

        self._tree: ClassTree = ClassTree(palette, self._vocabulary, reference_board)
        self._tree.classes_edited.connect(self._on_tree_edited)
        self._tree.edit_rejected.connect(self.message_posted)
        self._tree.itemSelectionChanged.connect(self._update_actions)
        self._tree.currentItemChanged.connect(self._update_actions)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)

        self._new_row_action: QAction = self._create_action(
            "New",
            "+ Text",
            "Add a row next to the selection: a class after a class, a phrase after a phrase; "
            + "a class at the end when nothing is selected.",
            self._tree.start_new_row,
        )
        self._new_class_action: QAction = self._create_action(
            "New Class", "+ Class", "Add a class after the selected class.", self._tree.start_new_class_after_selection
        )
        self._new_phrase_action: QAction = self._create_action(
            "New Phrase",
            "+ Phrase",
            "Add a phrase querying the selected class, e.g. suv for car.",
            self._tree.start_new_phrase_after_selection,
        )
        self._add_images_action: QAction = self._create_action(
            "Add Reference Images...", "+ Image", "", self._import_reference_images
        )
        self._remove_action: QAction = self._create_action(
            "Remove",
            "Remove",
            "Remove the selected classes, phrases or images (Delete).",
            self._tree.remove_selected_rows,
        )
        self._save_action: QAction = self._create_action(
            "Save Class Set...",
            "Save...",
            "Save the classes and their phrases as a named class set.",
            self._ask_name_and_save,
        )
        self._clear_action: QAction = self._create_action(
            "Clear All Classes", "Clear", "Remove every class.", self.clear
        )

        self._load_menu: QMenu = QMenu("Load Class Set", self)
        self._load_menu.setToolTipsVisible(True)
        self._load_menu.aboutToShow.connect(self._populate_load_menu)
        more_menu: QMenu = QMenu(self)
        more_menu.addMenu(self._load_menu)
        more_menu.addAction(self._save_action)
        more_menu.addSeparator()
        more_menu.addAction(self._clear_action)
        more_button: QToolButton = QToolButton()
        more_button.setText("\u22ef")
        more_button.setToolTip("Load, save or clear the classes.")
        more_button.setAutoRaise(True)
        more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_button.setMenu(more_menu)
        more_button.setStyleSheet("QToolButton::menu-indicator { image: none; }")

        self._remove_action.setIcon(TrashIcon(self.palette().color(QPalette.ColorRole.ButtonText)).to_icon())
        remove_button: QToolButton = self._tool_button_of(self._remove_action)
        remove_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        toolbar: QHBoxLayout = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(2)
        for action in (self._new_row_action, self._add_images_action):
            toolbar.addWidget(self._tool_button_of(action))
        toolbar.addStretch(1)
        toolbar.addWidget(remove_button)
        toolbar.addWidget(more_button)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(toolbar)
        layout.addWidget(self._tree, stretch=1)
        self._update_actions()

    @property
    def classes(self) -> tuple[ClassDefinition, ...]:
        """
        Classes in tree order.

        Returns
        -------
        tuple[ClassDefinition, ...]
            Classes whose index is the class id.
        """
        return self._vocabulary.classes

    @property
    def class_names(self) -> tuple[str, ...]:
        """
        Class names in tree order.

        Returns
        -------
        tuple[str, ...]
            Names whose index is the class id.
        """
        return self._vocabulary.class_names

    @property
    def current_class_name(self) -> str | None:
        """
        Class of the current row, or of the query the current row shows.

        Returns
        -------
        str | None
            ``None`` while no row is current.
        """
        return self._tree.current_class_name

    def restore(self, default_classes: tuple[ClassDefinition, ...]) -> None:
        """
        Replace every class with the classes remembered in the data directory.

        Parameters
        ----------
        default_classes : tuple[ClassDefinition, ...]
            Classes used when nothing has been remembered yet.
        """
        remembered_classes: tuple[ClassDefinition, ...] | None = self._class_list_store.load()
        self.set_classes(default_classes if remembered_classes is None else remembered_classes)

    def set_classes(self, definitions: Iterable[ClassDefinition]) -> None:
        """
        Replace every class.

        Parameters
        ----------
        definitions : Iterable[ClassDefinition]
            Classes to list; repeated names and phrases already used by an earlier class are dropped.
        """
        self._vocabulary.replace(definitions)
        self._board.retain_classes(self.class_names)
        self._refresh()
        self._report_change()

    def refresh_references(self) -> None:
        """
        Show the reference images of the board again, e.g. after images were added to it.
        """
        self._refresh()
        self._report_change()

    def set_image_prompt_supported(self, is_supported: bool) -> None:
        """
        Enable or disable adding reference images, and grey out reference images the backend would ignore.

        Parameters
        ----------
        is_supported : bool
            Whether the selected backend takes image prompts.
        """
        self._tree.set_image_prompt_supported(is_supported)
        self._update_actions()

    def save_class_set(self, name: str) -> None:
        """
        Store the classes as a named class set, replacing one of the same name.

        Parameters
        ----------
        name : str
            Class set name.

        Raises
        ------
        ValueError
            If the name is not usable as a file name.
        OSError
            If the class set cannot be written.
        """
        self._class_list_store.write_class_set(name, self.classes)
        self._class_set_name = name.strip()

    def load_class_set(self, name: str) -> None:
        """
        Replace every class with a saved class set.

        Parameters
        ----------
        name : str
            Class set name.

        Raises
        ------
        ValueError
            If the name is not usable, a line is not a valid class, or the class set lists no class.
        OSError
            If the class set cannot be read.
        """
        definitions: tuple[ClassDefinition, ...] = self._class_list_store.read_class_set(name)
        if not definitions:
            raise ValueError(f"Class set '{name}' lists no class.")
        self.set_classes(definitions)
        self._class_set_name = name.strip()

    def load_file(self, class_list_file: ClassListFile) -> None:
        """
        Replace every class with the classes of a class list file.

        Parameters
        ----------
        class_list_file : ClassListFile
            File listing one class per line.

        Raises
        ------
        OSError
            If the file cannot be read.
        ValueError
            If the file is not UTF-8 text, a line is not a valid class, or the file lists no class.
        """
        definitions: tuple[ClassDefinition, ...] = class_list_file.read()
        if not definitions:
            raise ValueError(f"No classes found in {class_list_file.path}.")
        self.set_classes(definitions)

    def start_new_row(self) -> None:
        """
        Add an empty row next to the selection, at the same level, to be named in place, as ``+`` does.
        """
        self._tree.start_new_row()

    def clear(self) -> None:
        """
        Remove every class.
        """
        self.set_classes(())

    def _create_action(self, text: str, icon_text: str, tool_tip: str, slot: Callable[[], None]) -> QAction:
        action: QAction = QAction(text, self)
        action.setIconText(icon_text)
        action.setToolTip(tool_tip)
        action.triggered.connect(lambda: slot())
        return action

    @staticmethod
    def _tool_button_of(action: QAction) -> QToolButton:
        tool_button: QToolButton = QToolButton()
        tool_button.setDefaultAction(action)
        tool_button.setAutoRaise(True)
        tool_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        return tool_button

    def _show_context_menu(self, position: QPoint) -> None:
        context_menu: QMenu = QMenu(self)
        context_menu.addAction(self._new_class_action)
        context_menu.addAction(self._new_phrase_action)
        context_menu.addAction(self._add_images_action)
        context_menu.addSeparator()
        context_menu.addAction(self._remove_action)
        context_menu.exec(self._tree.viewport().mapToGlobal(position))

    def _refresh(self) -> None:
        self._tree.populate()
        self._update_actions()

    def _report_change(self) -> None:
        try:
            self._class_list_store.save(self.classes)
        except OSError as error:
            self.message_posted.emit(f"Cannot remember classes: {error}")
        self.classes_changed.emit()

    def _on_tree_edited(self) -> None:
        self._update_actions()
        self._report_change()

    def _update_actions(self) -> None:
        is_class_current: bool = self.current_class_name is not None
        is_image_prompt_supported: bool = self._tree.is_image_prompt_supported
        self._remove_action.setEnabled(bool(self._tree.selectedItems()))
        self._new_phrase_action.setEnabled(bool(self._tree.selectedItems()))
        self._add_images_action.setEnabled(is_image_prompt_supported and is_class_current)
        self._add_images_action.setToolTip(
            "Add example images of the selected class; each image becomes one image query and is not analyzed."
            if is_image_prompt_supported
            else "The selected backend does not take image prompts."
        )
        self._save_action.setEnabled(bool(len(self._vocabulary)))
        self._clear_action.setEnabled(bool(len(self._vocabulary)))

    def _import_reference_images(self) -> None:
        class_name: str | None = self.current_class_name
        if class_name is None:
            return
        self._tree.expand_class(class_name)
        added_image_count: int = self._reference_importer.import_images(class_name, self.class_names)
        self.refresh_references()
        if added_image_count:
            self.message_posted.emit(
                f"Added {added_image_count} reference image{'' if added_image_count == 1 else 's'} "
                + f"for '{class_name}'."
            )

    def _populate_load_menu(self) -> None:
        self._load_menu.clear()
        class_set_names: tuple[str, ...] = self._class_list_store.class_set_names
        for name in class_set_names:
            self._load_menu.addAction(name, partial(self._load_class_set_interactively, name))
        if not class_set_names:
            self._load_menu.addAction("No saved class sets").setEnabled(False)
        self._load_menu.addSeparator()
        self._load_menu.addAction("From File...", self._choose_file_to_load)

    def _load_class_set_interactively(self, name: str) -> None:
        try:
            self.load_class_set(name)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot load classes", str(error))
            return
        self.message_posted.emit(f"Loaded class set '{name}'.")

    def _choose_file_to_load(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Classes", str(self._last_directory), self.FILE_FILTER)
        if not file_name:
            return
        path: Path = Path(file_name)
        self._last_directory = path.parent
        try:
            self.load_file(ClassListFile(path))
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot load classes", f"{path}\n{error}")
            return
        self.message_posted.emit(f"Loaded classes from {path.name}.")

    def _ask_name_and_save(self) -> None:
        name, is_accepted = QInputDialog.getText(
            self, "Save Class Set", "Class set name:", QLineEdit.EchoMode.Normal, self._class_set_name
        )
        name = name.strip()
        if not is_accepted or not name:
            return
        try:
            if (
                self._class_list_store.has_class_set(name)
                and QMessageBox.question(self, "Save Class Set", f"Replace the class set '{name}'?")
                != QMessageBox.StandardButton.Yes
            ):
                return
            self.save_class_set(name)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot save classes", str(error))
            return
        self.message_posted.emit(f"Saved class set '{name}'.")
