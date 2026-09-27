from functools import partial
from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QKeyEvent
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QStyle, QTreeWidget, QTreeWidgetItem, QWidget

from ...detection import ReferenceBoard
from ...vocabulary import ClassDefinition, ClassVocabulary
from ..class_palette import ClassPalette


class ClassTree(QTreeWidget):
    """
    Tree view of a class vocabulary and its reference images, edited in place.

    Each top-level row is an output class (its position is the class id, its icon the box color); its child rows are
    the queries the model reads for it: phrases, then reference images (the boxes of one image form one visual
    query). Class names and phrases are renamed by editing their rows; an edit that blanks a name or reuses a name or
    phrase of another class is reverted. Delete or Backspace removes the selected rows, be they classes, phrases or
    reference images. Reference images are greyed out while the backend takes no image prompts.

    The tree shares the vocabulary and the reference board with its owner, who calls ``populate`` after changing
    them.

    Signals
    -------
    classes_edited : Signal()
        A class or phrase was renamed, or rows were removed, from the tree.
    edit_rejected : Signal(str)
        Reason an in-place edit was reverted.
    """

    classes_edited: Signal = Signal()
    edit_rejected: Signal = Signal(str)

    HEADERS: tuple[str, ...] = ("Class / Query", "ID", "#")
    NAME_COLUMN = 0
    ID_COLUMN = 1
    QUERY_COUNT_COLUMN = 2
    MINIMUM_HEIGHT = 160
    IGNORED_COLOR = QColor("#8a8a8a")
    WARNING_COLOR = QColor("#d9822b")
    REMOVE_KEYS: frozenset[Qt.Key] = frozenset({Qt.Key.Key_Delete, Qt.Key.Key_Backspace})

    def __init__(
        self,
        palette: ClassPalette,
        vocabulary: ClassVocabulary,
        reference_board: ReferenceBoard,
        parent: QWidget | None = None,
    ) -> None:
        """
        Parameters
        ----------
        palette : ClassPalette
            Colors of the classes.
        vocabulary : ClassVocabulary
            Classes shown as top-level rows; renamed and reduced by edits in the tree.
        reference_board : ReferenceBoard
            Reference boxes shown as reference image rows; kept in step with renamed and removed classes.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._palette: ClassPalette = palette
        self._vocabulary: ClassVocabulary = vocabulary
        self._board: ReferenceBoard = reference_board
        self._expanded_class_names: set[str] = set()
        self._is_populating: bool = False
        self._is_image_prompt_supported: bool = True

        self.setColumnCount(len(self.HEADERS))
        self.setHeaderLabels(list(self.HEADERS))
        self.headerItem().setToolTip(
            self.QUERY_COUNT_COLUMN, "Number of queries the selected model reads for the class."
        )
        header: QHeaderView = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(self.NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.ID_COLUMN, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.QUERY_COUNT_COLUMN, QHeaderView.ResizeMode.ResizeToContents)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.setAlternatingRowColors(True)
        self.setToolTip(
            "Double-click a class or phrase to edit it; Delete removes the selected classes, phrases or images."
        )
        self.setMinimumHeight(self.MINIMUM_HEIGHT)
        self.setAcceptDrops(False)
        self.itemChanged.connect(self._on_item_changed)
        self.itemExpanded.connect(partial(self._on_expansion_changed, is_expanded=True))
        self.itemCollapsed.connect(partial(self._on_expansion_changed, is_expanded=False))

    @property
    def is_image_prompt_supported(self) -> bool:
        """
        Whether reference images are counted as queries of their class.

        Returns
        -------
        bool
            False while the selected backend takes no image prompts.
        """
        return self._is_image_prompt_supported

    @property
    def current_class_name(self) -> str | None:
        """
        Class of the current row, or of the query the current row shows.

        Returns
        -------
        str | None
            ``None`` while no row is current.
        """
        item: QTreeWidgetItem | None = self.currentItem()
        if item is None:
            return None
        class_item: QTreeWidgetItem = item.parent() or item
        class_index: int = self.indexOfTopLevelItem(class_item)
        return self._vocabulary.class_names[class_index] if 0 <= class_index < len(self._vocabulary) else None

    def set_image_prompt_supported(self, is_supported: bool) -> None:
        """
        Count or grey out the reference images, and show the tree again.

        Parameters
        ----------
        is_supported : bool
            Whether the selected backend takes image prompts.
        """
        self._is_image_prompt_supported = is_supported
        self.populate()

    def expand_class(self, class_name: str) -> None:
        """
        Show the queries of a class expanded from the next ``populate`` on.

        Parameters
        ----------
        class_name : str
            Class to expand.
        """
        self._expanded_class_names.add(class_name)

    def populate(self) -> None:
        """
        Rebuild every row from the vocabulary and the reference board, keeping the current row where possible.
        """
        current_position: tuple[int, int] | None = self._current_position()
        self._is_populating = True
        self.clear()
        for class_index, definition in enumerate(self._vocabulary.classes):
            class_item: QTreeWidgetItem = self._class_item_of(class_index, definition)
            self.addTopLevelItem(class_item)
            class_item.setExpanded(definition.name in self._expanded_class_names)
        self._is_populating = False
        self._restore_current(current_position)

    def remove_selected_rows(self) -> None:
        """
        Remove the selected classes, phrases and reference images.
        """
        selected_items: list[QTreeWidgetItem] = self.selectedItems()
        if not selected_items:
            return
        removed_classes: set[int] = set()
        removed_phrases: dict[int, set[int]] = {}
        removed_images: list[tuple[str, Path]] = []
        for item in selected_items:
            parent: QTreeWidgetItem | None = item.parent()
            if parent is None:
                removed_classes.add(self.indexOfTopLevelItem(item))
                continue
            class_index: int = self.indexOfTopLevelItem(parent)
            definition: ClassDefinition = self._vocabulary.classes[class_index]
            child_index: int = parent.indexOfChild(item)
            if child_index < len(definition.text_queries):
                removed_phrases.setdefault(class_index, set()).add(child_index)
            else:
                image_paths: tuple[Path, ...] = self._board.reference_images_of(definition.name)
                removed_images.append((definition.name, image_paths[child_index - len(definition.text_queries)]))
        for class_name, image_path in removed_images:
            self._board.remove_reference_image(class_name, image_path)
        for class_index, phrase_indices in removed_phrases.items():
            self._vocabulary.remove_phrases(class_index, phrase_indices)
        self._vocabulary.remove_classes(removed_classes)
        self._board.retain_classes(self._vocabulary.class_names)
        self.clearSelection()
        self.populate()
        self.classes_edited.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if Qt.Key(event.key()) in self.REMOVE_KEYS and self.selectedItems():
            self.remove_selected_rows()
            event.accept()
            return
        super().keyPressEvent(event)

    def _class_item_of(self, class_index: int, definition: ClassDefinition) -> QTreeWidgetItem:
        image_paths: tuple[Path, ...] = self._board.reference_images_of(definition.name)
        used_image_count: int = len(image_paths) if self._is_image_prompt_supported else 0
        query_count: int = len(definition.text_queries) + used_image_count
        class_item: QTreeWidgetItem = QTreeWidgetItem([definition.name, str(class_index), str(query_count)])
        class_item.setIcon(self.NAME_COLUMN, self._palette.swatch_of(class_index))
        class_item.setFlags(class_item.flags() | Qt.ItemFlag.ItemIsEditable)
        class_item.setTextAlignment(self.ID_COLUMN, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        class_item.setTextAlignment(
            self.QUERY_COUNT_COLUMN, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        class_item.setToolTip(
            self.QUERY_COUNT_COLUMN,
            f"{len(definition.text_queries)} phrase{'' if len(definition.text_queries) == 1 else 's'}, "
            + f"{used_image_count} reference image{'' if used_image_count == 1 else 's'}",
        )
        if query_count == 0:
            class_item.setForeground(self.NAME_COLUMN, QBrush(self.WARNING_COLOR))
            class_item.setToolTip(self.NAME_COLUMN, "No query the selected model can use; add a phrase.")
        for phrase in definition.text_queries:
            phrase_item: QTreeWidgetItem = QTreeWidgetItem([phrase, "", ""])
            phrase_item.setFlags(phrase_item.flags() | Qt.ItemFlag.ItemIsEditable)
            phrase_item.setToolTip(self.NAME_COLUMN, f"Phrase querying '{definition.name}'; double-click to edit.")
            class_item.addChild(phrase_item)
        for image_path in image_paths:
            class_item.addChild(self._reference_item_of(definition.name, image_path))
        return class_item

    def _reference_item_of(self, class_name: str, image_path: Path) -> QTreeWidgetItem:
        box_count: int = len(self._board.boxes_of(class_name, image_path))
        reference_item: QTreeWidgetItem = QTreeWidgetItem(
            [f"{image_path.name} ({box_count} box{'' if box_count == 1 else 'es'})", "", ""]
        )
        reference_item.setIcon(self.NAME_COLUMN, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        if self._is_image_prompt_supported:
            reference_item.setToolTip(self.NAME_COLUMN, f"Reference image querying '{class_name}'\n{image_path}")
        else:
            reference_item.setForeground(self.NAME_COLUMN, QBrush(self.IGNORED_COLOR))
            reference_item.setToolTip(
                self.NAME_COLUMN, f"Ignored: the selected backend does not take image prompts.\n{image_path}"
            )
        return reference_item

    def _current_position(self) -> tuple[int, int] | None:
        item: QTreeWidgetItem | None = self.currentItem()
        if item is None:
            return None
        parent: QTreeWidgetItem | None = item.parent()
        if parent is None:
            return (self.indexOfTopLevelItem(item), -1)
        return (self.indexOfTopLevelItem(parent), parent.indexOfChild(item))

    def _restore_current(self, position: tuple[int, int] | None) -> None:
        if position is None:
            return
        class_index, child_index = position
        class_item: QTreeWidgetItem | None = self.topLevelItem(min(class_index, self.topLevelItemCount() - 1))
        if class_item is None:
            return
        child_item: QTreeWidgetItem | None = class_item.child(child_index) if child_index >= 0 else None
        self.setCurrentItem(child_item or class_item, 0, QItemSelectionModel.SelectionFlag.NoUpdate)

    def _on_expansion_changed(self, item: QTreeWidgetItem, is_expanded: bool) -> None:
        if self._is_populating or item.parent() is not None:
            return
        class_name: str = item.text(self.NAME_COLUMN)
        if is_expanded:
            self._expanded_class_names.add(class_name)
        else:
            self._expanded_class_names.discard(class_name)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._is_populating or column != self.NAME_COLUMN:
            return
        parent: QTreeWidgetItem | None = item.parent()
        try:
            if parent is None:
                self._rename_class(item)
            else:
                self._rename_phrase(parent, item)
        except ValueError as error:
            self.edit_rejected.emit(str(error))
            self._revert_item(item)
            return
        self.classes_edited.emit()

    def _rename_class(self, class_item: QTreeWidgetItem) -> None:
        class_index: int = self.indexOfTopLevelItem(class_item)
        previous: ClassDefinition = self._vocabulary.rename_class(class_index, class_item.text(self.NAME_COLUMN))
        renamed: ClassDefinition = self._vocabulary.classes[class_index]
        self._board.rename_class(previous.name, renamed.name)
        if previous.name in self._expanded_class_names:
            self._expanded_class_names.discard(previous.name)
            self._expanded_class_names.add(renamed.name)
        self._is_populating = True
        class_item.setText(self.NAME_COLUMN, renamed.name)
        for phrase_index, phrase in enumerate(renamed.text_queries):
            phrase_item: QTreeWidgetItem | None = class_item.child(phrase_index)
            if phrase_item is not None:
                phrase_item.setText(self.NAME_COLUMN, phrase)
        self._is_populating = False

    def _rename_phrase(self, class_item: QTreeWidgetItem, phrase_item: QTreeWidgetItem) -> None:
        class_index: int = self.indexOfTopLevelItem(class_item)
        phrase_index: int = class_item.indexOfChild(phrase_item)
        self._vocabulary.rename_phrase(class_index, phrase_index, phrase_item.text(self.NAME_COLUMN))
        self._is_populating = True
        phrase_item.setText(self.NAME_COLUMN, self._vocabulary.classes[class_index].text_queries[phrase_index])
        self._is_populating = False

    def _revert_item(self, item: QTreeWidgetItem) -> None:
        parent: QTreeWidgetItem | None = item.parent()
        self._is_populating = True
        if parent is None:
            item.setText(self.NAME_COLUMN, self._vocabulary.classes[self.indexOfTopLevelItem(item)].name)
        else:
            definition: ClassDefinition = self._vocabulary.classes[self.indexOfTopLevelItem(parent)]
            item.setText(self.NAME_COLUMN, definition.text_queries[parent.indexOfChild(item)])
        self._is_populating = False
