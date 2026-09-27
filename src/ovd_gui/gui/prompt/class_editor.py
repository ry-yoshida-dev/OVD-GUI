from collections.abc import Iterable
from functools import partial
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...detection import ReferenceBoard
from ...vocabulary import ClassDefinition, ClassListFile, ClassListStore, ClassVocabulary
from ..class_palette import ClassPalette
from .class_tree import ClassTree
from .reference_image_importer import ReferenceImageImporter


class ClassEditor(QWidget):
    """
    Editor of the classes to detect and their queries: a ``ClassTree`` with an input field and buttons below.

    The input field adds classes: ``cat, dog`` adds two classes queried by their names, ``car: car, suv, taxi`` adds
    one class queried by the listed phrases, and naming an existing class adds the phrases to it. Enter in the empty
    field requests a detection. ``Add Phrases...`` and ``Add Images...`` (reference images) act on the class of the
    current row; adding images is disabled while the backend takes no image prompts.

    ``Save...`` asks only for a name and stores the classes and phrases as a class set in the data directory;
    ``Load`` replaces them with a saved class set picked from its menu, or with any class list text file.
    The classes are also remembered in the data directory after every change, to be restored at the next start.
    Reference images are kept for the session only.

    Signals
    -------
    classes_changed : Signal()
        A class, phrase or reference image was added, renamed or removed.
    detection_requested : Signal()
        The user pressed Enter with nothing left to add.
    message_posted : Signal(str)
        A short notice for the status bar, e.g. that a class set was saved or an edit was rejected.
    """

    classes_changed: Signal = Signal()
    detection_requested: Signal = Signal()
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
        self._tree.itemSelectionChanged.connect(self._update_buttons)
        self._tree.currentItemChanged.connect(self._update_buttons)

        self._input_edit: QLineEdit = QLineEdit()
        self._input_edit.setPlaceholderText("cat, dog  or  car: car, suv, taxi")
        self._input_edit.setToolTip(
            "Comma-separated names add classes queried by their names; "
            + "'name: phrase, phrase' adds a class queried by the phrases."
        )
        self._input_edit.setClearButtonEnabled(True)
        self._input_edit.setAcceptDrops(False)
        self._input_edit.returnPressed.connect(self._on_return_pressed)
        add_button: QPushButton = QPushButton("Add")
        add_button.clicked.connect(self.commit_pending_text)
        input_row: QHBoxLayout = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.addWidget(self._input_edit, stretch=1)
        input_row.addWidget(add_button)

        self._phrase_button: QPushButton = QPushButton("Add Phrases...")
        self._phrase_button.setToolTip("Add phrases querying the selected class, e.g. suv, taxi for car.")
        self._phrase_button.clicked.connect(self._ask_phrases)
        self._reference_button: QPushButton = QPushButton("Add Images...")
        self._reference_button.clicked.connect(self._import_reference_images)
        self._remove_button: QPushButton = QPushButton("Remove")
        self._remove_button.clicked.connect(self._tree.remove_selected_rows)
        query_row: QHBoxLayout = QHBoxLayout()
        query_row.setContentsMargins(0, 0, 0, 0)
        query_row.addWidget(self._phrase_button, stretch=1)
        query_row.addWidget(self._reference_button, stretch=1)
        query_row.addWidget(self._remove_button)

        clear_button: QPushButton = QPushButton("Clear")
        clear_button.clicked.connect(self.clear)
        self._load_menu: QMenu = QMenu(self)
        self._load_menu.aboutToShow.connect(self._populate_load_menu)
        load_button: QPushButton = QPushButton("Load")
        load_button.setToolTip("Replace the classes with a saved class set or a class list text file.")
        load_button.setMenu(self._load_menu)
        self._save_button: QPushButton = QPushButton("Save...")
        self._save_button.setToolTip("Save the classes and their phrases as a named class set.")
        self._save_button.clicked.connect(self._ask_name_and_save)
        footer: QHBoxLayout = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addWidget(load_button)
        footer.addWidget(self._save_button)
        footer.addStretch(1)
        footer.addWidget(clear_button)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._tree, stretch=1)
        layout.addLayout(input_row)
        layout.addLayout(query_row)
        layout.addLayout(footer)
        self._update_buttons()

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

    def add_phrases(self, class_name: str, text: str) -> None:
        """
        Add comma-separated phrases to a class.

        Parameters
        ----------
        class_name : str
            Class to extend.
        text : str
            Phrases separated by ``,``.

        Raises
        ------
        KeyError
            If no class has the name.
        ValueError
            If a phrase is invalid or already queries another class.
        """
        index: int | None = self._vocabulary.index_of(class_name)
        if index is None:
            raise KeyError(f"No class named '{class_name}'.")
        self._vocabulary.add_phrases(index, ClassDefinition.split_phrases(text))
        self._tree.expand_class(self.class_names[index])
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
        self._update_buttons()

    def commit_pending_text(self) -> None:
        """
        Add the classes still in the input field.

        The text stays in the field when a class cannot be added, and the reason is posted.
        """
        text: str = self._input_edit.text()
        if not text.strip():
            return
        try:
            for definition in self._parse_input(text):
                index: int = self._vocabulary.add(definition)
                if not definition.is_named_query:
                    self._tree.expand_class(self.class_names[index])
        except ValueError as error:
            self.message_posted.emit(str(error))
            self._refresh()
            self._report_change()
            return
        self._input_edit.clear()
        self._refresh()
        self._tree.scrollToBottom()
        self._report_change()

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
        self._input_edit.clear()
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
        self._input_edit.clear()
        self.set_classes(definitions)

    def clear(self) -> None:
        """
        Remove every class and the pending text.
        """
        self._input_edit.clear()
        self.set_classes(())
        self._input_edit.setFocus()

    @staticmethod
    def _parse_input(text: str) -> tuple[ClassDefinition, ...]:
        if ClassDefinition.QUERY_SEPARATOR in text:
            return (ClassDefinition.parse(text),)
        return tuple(ClassDefinition.named(name) for name in ClassDefinition.split_phrases(text))

    def _refresh(self) -> None:
        self._tree.populate()
        self._update_buttons()

    def _report_change(self) -> None:
        try:
            self._class_list_store.save(self.classes)
        except OSError as error:
            self.message_posted.emit(f"Cannot remember classes: {error}")
        self.classes_changed.emit()

    def _on_tree_edited(self) -> None:
        self._update_buttons()
        self._report_change()

    def _update_buttons(self) -> None:
        is_class_current: bool = self.current_class_name is not None
        is_image_prompt_supported: bool = self._tree.is_image_prompt_supported
        self._remove_button.setEnabled(bool(self._tree.selectedItems()))
        self._phrase_button.setEnabled(is_class_current)
        self._reference_button.setEnabled(is_image_prompt_supported and is_class_current)
        self._reference_button.setToolTip(
            "Add example images of the selected class; each image becomes one image query and is not analyzed."
            if is_image_prompt_supported
            else "The selected backend does not take image prompts."
        )
        self._save_button.setEnabled(bool(len(self._vocabulary)))

    def _ask_phrases(self) -> None:
        class_name: str | None = self.current_class_name
        if class_name is None:
            return
        text, is_accepted = QInputDialog.getText(
            self, "Add Phrases", f"Phrases querying '{class_name}' (comma-separated):"
        )
        if not is_accepted or not text.strip():
            return
        try:
            self.add_phrases(class_name, text)
        except ValueError as error:
            QMessageBox.warning(self, "Cannot add phrases", str(error))

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
        self.commit_pending_text()
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

    def _on_return_pressed(self) -> None:
        if self._input_edit.text().strip():
            self.commit_pending_text()
            return
        self.detection_requested.emit()
