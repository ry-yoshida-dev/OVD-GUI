from collections.abc import Callable, Iterable
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...detection import ReferenceBoard
from ...storage import ClassSet, ClassSetArchive, ClassSetStore
from ...vocabulary import ClassDefinition, ClassListFile, ClassListStore, ClassVocabulary
from ..class_palette import ClassPalette
from .class_set_dialog import ClassSetDialog
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
    of the tree offers ``New Class`` and ``New Prompt`` explicitly, besides the image and remove actions.

    The ``Set`` drop-down above the toolbar lists the class sets saved in the data directory, like the preset
    drop-down of the model settings: choosing one loads it, after confirming when the current classes were edited,
    and ``Edited`` marks changes since the set was loaded or saved. The ``⋯`` menu holds the class sets: ``Class Sets...`` opens the ``ClassSetDialog`` library to preview, load,
    rename, delete, import or export saved sets; ``Save Class Set...`` asks only for a name and stores the classes,
    their phrases and their reference images (pixels included) as one archive in the data directory; ``Load From
    File...`` takes a class set archive or any class list text file; ``Clear`` removes every class. The classes and
    phrases are also remembered in the data directory after every change, to be restored at the next start;
    reference images come back only through a class set.

    Signals
    -------
    classes_changed : Signal()
        A class, phrase or reference image was added, renamed or removed.
    message_posted : Signal(str)
        A short notice for the status bar, e.g. that a class set was saved or an entry was rejected.
    """

    classes_changed: Signal = Signal()
    message_posted: Signal = Signal(str)

    UNSAVED_PLACEHOLDER = "Unsaved classes"
    FILE_FILTER: str = (
        f"Class sets (*{ClassSetArchive.SUFFIX});;"
        + "Class lists ("
        + " ".join(f"*{suffix}" for suffix in ClassListFile.SUFFIXES)
        + ");;All files (*)"
    )

    def __init__(
        self,
        palette: ClassPalette,
        class_list_store: ClassListStore,
        class_set_store: ClassSetStore,
        reference_board: ReferenceBoard,
        parent: QWidget | None = None,
    ) -> None:
        """
        Parameters
        ----------
        palette : ClassPalette
            Colors of the classes.
        class_list_store : ClassListStore
            Data directory remembering the classes between runs.
        class_set_store : ClassSetStore
            Data directory holding the saved class sets.
        reference_board : ReferenceBoard
            Reference boxes shown under their classes; kept in step with renamed and removed classes.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._vocabulary: ClassVocabulary = ClassVocabulary()
        self._board: ReferenceBoard = reference_board
        self._class_list_store: ClassListStore = class_list_store
        self._class_set_store: ClassSetStore = class_set_store
        self._class_set_name: str = ""
        self._is_edited: bool = False
        self._last_directory: Path = class_set_store.class_set_directory
        self._reference_importer: ReferenceImageImporter = ReferenceImageImporter(palette, reference_board, self)
        self._class_set_dialog: ClassSetDialog = ClassSetDialog(class_set_store, palette, self)

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
            "Add a row next to the selection: a class after a class, a prompt after a prompt; "
            + "a class at the end when nothing is selected.",
            self._tree.start_new_row,
        )
        self._new_class_action: QAction = self._create_action(
            "New Class", "+ Class", "Add a class after the selected class.", self._tree.start_new_class_after_selection
        )
        self._new_phrase_action: QAction = self._create_action(
            "New Prompt",
            "+ Prompt",
            "Add a text prompt for the selected class, e.g. suv for car.",
            self._tree.start_new_phrase_after_selection,
        )
        self._add_images_action: QAction = self._create_action(
            "Add Reference Images...", "+ Image", "", self._import_reference_images
        )
        self._remove_action: QAction = self._create_action(
            "Remove",
            "Remove",
            "Remove the selected classes, prompts or images (Delete).",
            self._tree.remove_selected_rows,
        )
        self._save_action: QAction = self._create_action(
            "Save Class Set...",
            "Save...",
            "Save the classes with their text prompts and reference images as a named class set.",
            self._ask_name_and_save,
        )
        self._clear_action: QAction = self._create_action(
            "Clear All Classes", "Clear", "Remove every class.", self.clear
        )

        self._library_action: QAction = self._create_action(
            "Class Sets...",
            "Class Sets...",
            "Browse, load, rename, delete, import or export the saved class sets.",
            self._open_class_set_library,
        )
        self._load_file_action: QAction = self._create_action(
            "Load From File...",
            "Load From File...",
            "Replace the classes with a class set archive or a class list text file.",
            self._choose_file_to_load,
        )
        more_menu: QMenu = QMenu(self)
        more_menu.setToolTipsVisible(True)
        more_menu.addAction(self._library_action)
        more_menu.addAction(self._save_action)
        more_menu.addAction(self._load_file_action)
        more_menu.addSeparator()
        more_menu.addAction(self._clear_action)
        more_button: QToolButton = QToolButton()
        more_button.setText("\u22ef")
        more_button.setToolTip("Class sets: browse, save and load; clear the classes.")
        more_button.setAutoRaise(True)
        more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_button.setMenu(more_menu)
        more_button.setStyleSheet("QToolButton::menu-indicator { image: none; }")

        self._remove_action.setIcon(TrashIcon(self.palette().color(QPalette.ColorRole.ButtonText)).to_icon())
        remove_button: QToolButton = self._tool_button_of(self._remove_action)
        remove_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        self._set_combo: QComboBox = QComboBox()
        self._set_combo.setPlaceholderText(self.UNSAVED_PLACEHOLDER)
        self._set_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._set_combo.setMinimumContentsLength(8)
        self._set_combo.activated.connect(self._on_set_chosen)
        self._edited_label: QLabel = QLabel("Edited")
        self._edited_label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        self._edited_label.setToolTip("The classes changed since the class set was loaded or saved.")
        set_row: QHBoxLayout = QHBoxLayout()
        set_row.setContentsMargins(0, 0, 0, 0)
        set_row.setSpacing(6)
        set_row.addWidget(QLabel("Set"))
        set_row.addWidget(self._set_combo, stretch=1)
        set_row.addWidget(self._edited_label)
        set_row.addWidget(self._tool_button_of(self._save_action))

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
        layout.addLayout(set_row)
        layout.addLayout(toolbar)
        layout.addWidget(self._tree, stretch=1)
        self._update_actions()
        self.refresh_class_sets()

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
        self._associate("")

    @property
    def class_set_name(self) -> str:
        """
        Saved class set the classes were last loaded from or saved to.

        Returns
        -------
        str
            Set name selected in the ``Set`` drop-down; empty for classes not tied to a saved set.
        """
        return self._class_set_name

    @property
    def is_edited(self) -> bool:
        """
        Whether the classes changed since they were restored, loaded or saved.

        Returns
        -------
        bool
            True after any edit of classes, phrases or reference images.
        """
        return self._is_edited

    def refresh_class_sets(self) -> None:
        """
        List the saved class sets in the ``Set`` drop-down again, e.g. after sets were added, renamed or deleted.
        """
        if self._class_set_name and not self._class_set_store.has_class_set(self._class_set_name):
            self._class_set_name = ""
        names: tuple[str, ...] = self._class_set_store.class_set_names
        self._set_combo.blockSignals(True)
        self._set_combo.clear()
        self._set_combo.addItems(list(names))
        self._set_combo.setCurrentIndex(names.index(self._class_set_name) if self._class_set_name in names else -1)
        self._set_combo.blockSignals(False)
        self._set_combo.setEnabled(bool(names))
        self._set_combo.setToolTip(
            f"Class sets saved in {self._class_set_store.class_set_directory}; choose one to load it."
            if names
            else "No class set saved yet; save the classes to list them here."
        )
        self._update_edited_label()

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
        Store the classes, their phrases and their reference images as a named class set, replacing one of the same
        name.

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
        self._class_set_store.write_class_set(name, ClassSet.of(self.classes, self._board))
        self._associate(name.strip())

    def load_class_set(self, name: str) -> None:
        """
        Replace every class and reference image with a saved class set.

        Parameters
        ----------
        name : str
            Class set name.

        Raises
        ------
        ValueError
            If the name is not usable, the class set is invalid, or it lists no class.
        OSError
            If the class set cannot be read.
        """
        self._apply_class_set(self._class_set_store.read_class_set(name), name)
        self._associate(name.strip())

    def load_file(self, path: Path) -> None:
        """
        Replace every class with the classes of a file.

        A class set archive also replaces every reference image; a class list text file keeps the reference images of
        the classes it lists.

        Parameters
        ----------
        path : Path
            Class set archive (``.ovdset``) or text file listing one class per line.

        Raises
        ------
        OSError
            If the file cannot be read.
        ValueError
            If the file content is invalid or the file lists no class.
        """
        if ClassSetArchive.is_archive_path(path):
            self._apply_class_set(ClassSetArchive(path).read(), path.name)
        else:
            definitions: tuple[ClassDefinition, ...] = ClassListFile(path).read()
            if not definitions:
                raise ValueError(f"No classes found in {path}.")
            self.set_classes(definitions)
        self._associate("")

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

    def _associate(self, name: str) -> None:
        self._class_set_name = name
        self._is_edited = False
        self.refresh_class_sets()

    def _update_edited_label(self) -> None:
        self._edited_label.setVisible(bool(self._class_set_name) and self._is_edited)

    def _on_set_chosen(self, index: int) -> None:
        name: str = self._set_combo.itemText(index)
        if name == self._class_set_name and not self._is_edited:
            return
        if (
            self._is_edited
            and self.classes
            and QMessageBox.question(
                self,
                "Load Class Set",
                f"Load the class set '{name}' and discard the edits to the current classes?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            self.refresh_class_sets()
            return
        self._load_class_set_interactively(name)
        self.refresh_class_sets()

    def _apply_class_set(self, class_set: ClassSet, source_name: str) -> None:
        if not class_set.classes:
            raise ValueError(f"Class set '{source_name}' lists no class.")
        self._board.replace(class_set.reference_boxes, class_set.reference_pixels)
        self.set_classes(class_set.classes)

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
        self._is_edited = True
        self._update_edited_label()
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
            "Add example images of the selected class; each image becomes one image prompt and is not analyzed."
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

    def _open_class_set_library(self) -> None:
        name: str | None = self._class_set_dialog.ask(self._class_set_name)
        self._class_set_name = self._class_set_dialog.name_after_renames(self._class_set_name)
        self.refresh_class_sets()
        if name is not None:
            self._load_class_set_interactively(name)

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
            self.load_file(path)
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
                self._class_set_store.has_class_set(name)
                and QMessageBox.question(self, "Save Class Set", f"Replace the class set '{name}'?")
                != QMessageBox.StandardButton.Yes
            ):
                return
            self.save_class_set(name)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot save classes", str(error))
            return
        self.message_posted.emit(f"Saved class set '{name}'.")
