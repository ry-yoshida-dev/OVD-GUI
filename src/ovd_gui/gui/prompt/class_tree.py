from functools import partial

from PySide6.QtCore import QItemSelectionModel, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QDragEnterEvent, QDragMoveEvent, QDropEvent, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemDelegate,
    QAbstractItemView,
    QHeaderView,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from ...detection import ReferenceBoard, ReferenceImage
from ...vocabulary import ClassDefinition, ClassVocabulary
from ..class_palette import ClassPalette
from .placeholder_item_delegate import PlaceholderItemDelegate
from .query_drop_kind import QueryDropKind
from .query_drop_target import QueryDropTarget


class ClassTree(QTreeWidget):
    """
    Tree view of a class vocabulary and its reference images, edited in place.

    Each top-level row is an output class (its position is the class id, its icon the box color); its child rows are
    the queries the model reads for it: phrases, then reference images (the boxes of one image form one visual
    query). Class names and phrases are renamed by editing their rows; an edit that blanks a name or reuses a name or
    phrase of another class is reverted. Delete or Backspace removes the selected rows, be they classes, phrases or
    reference images. Reference images are greyed out while the backend takes no image prompts.

    Classes and phrases are added the same way, as in a file explorer: ``start_new_row`` inserts an empty row next to
    the selection, at the same level (a class after a selected class, a phrase after a selected query, a class at the
    end when nothing is selected), and opens its editor. Enter adds what was typed (``car: car, suv`` also names the
    phrases of a new class, and ``suv, taxi`` adds two phrases); a rejected entry is reported and its editor reopened.
    Escape, or leaving the row empty, drops the row. Double-clicking the empty area below the rows starts a new class.

    Query rows are dragged to move them: dropped on a class or among its queries, the query joins that class at that
    place; dropped between classes or below the rows, a phrase becomes a class of its own (``van`` becomes the class
    ``van``). Reference images can only move to another class. Class rows are not dragged.

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

    HEADERS: tuple[str, ...] = ("Class / Prompt", "ID", "#")
    NAME_COLUMN = 0
    ID_COLUMN = 1
    QUERY_COUNT_COLUMN = 2
    MINIMUM_HEIGHT = 160
    NEW_CLASS_PLACEHOLDER = "Class name, e.g. car"
    NEW_PHRASE_PLACEHOLDER = "Prompt, e.g. suv"
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
        self._pending_item: QTreeWidgetItem | None = None
        self._delegate: PlaceholderItemDelegate = PlaceholderItemDelegate(self)
        self.setItemDelegate(self._delegate)
        self._delegate.closeEditor.connect(self._on_editor_closed)

        self.setColumnCount(len(self.HEADERS))
        self.setHeaderLabels(list(self.HEADERS))
        self.headerItem().setToolTip(
            self.QUERY_COUNT_COLUMN, "Number of prompts the selected model reads for the class."
        )
        header: QHeaderView = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(self.NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.ID_COLUMN, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.QUERY_COUNT_COLUMN, QHeaderView.ResizeMode.ResizeToContents)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.setAlternatingRowColors(True)
        self.setToolTip(
            "Double-click a class or prompt to edit it, or the empty area to add a class; "
            + "Delete removes the selected classes, prompts or images."
        )
        self.setMinimumHeight(self.MINIMUM_HEIGHT)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
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

    def start_new_row(self) -> None:
        """
        Insert an empty row next to the selection, at the same level, and open its editor.

        A selected class gets a new class after it, a selected phrase or reference image a new phrase after it in the
        same class; without a selection a class is appended.
        """
        selected_item: QTreeWidgetItem | None = self._selected_item()
        if selected_item is not None and selected_item.parent() is not None:
            self.start_new_phrase_after_selection()
        else:
            self.start_new_class_after_selection()

    def start_new_class_after_selection(self) -> None:
        """
        Insert an empty class row after the class of the selected row, or at the end, and open its editor.
        """
        selected_item: QTreeWidgetItem | None = self._selected_item()
        if selected_item is None:
            self.start_new_class()
            return
        class_item: QTreeWidgetItem = selected_item.parent() or selected_item
        self.start_new_class(position=self.indexOfTopLevelItem(class_item) + 1)

    def start_new_phrase_after_selection(self) -> None:
        """
        Insert an empty phrase row after the selected phrase, or after the phrases of the selected class, and open its
        editor; nothing happens without a selection.
        """
        selected_item: QTreeWidgetItem | None = self._selected_item()
        if selected_item is None:
            return
        parent: QTreeWidgetItem | None = selected_item.parent()
        class_item: QTreeWidgetItem = parent or selected_item
        class_index: int = self.indexOfTopLevelItem(class_item)
        phrase_count: int = len(self._vocabulary.classes[class_index].text_queries)
        position: int = phrase_count if parent is None else min(parent.indexOfChild(selected_item) + 1, phrase_count)
        self.start_new_phrase(self._vocabulary.class_names[class_index], position=position)

    def start_new_class(self, text: str = "", position: int | None = None) -> None:
        """
        Insert an empty class row and open its editor.

        Parameters
        ----------
        text : str, optional
            Text the editor starts with.
        position : int | None, optional
            Class id of the new class; ``None`` appends it.
        """
        class_index: int = len(self._vocabulary) if position is None else min(position, len(self._vocabulary))
        class_item: QTreeWidgetItem = QTreeWidgetItem(["", str(class_index), ""])
        class_item.setIcon(self.NAME_COLUMN, self._palette.swatch_of(class_index))
        class_item.setTextAlignment(self.ID_COLUMN, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.insertTopLevelItem(class_index, class_item)
        self._edit_pending(class_item, text, self.NEW_CLASS_PLACEHOLDER)

    def start_new_phrase(self, class_name: str, text: str = "", position: int | None = None) -> None:
        """
        Insert an empty phrase row into a class and open its editor.

        Parameters
        ----------
        class_name : str
            Class the phrase will query.
        text : str, optional
            Text the editor starts with.
        position : int | None, optional
            Position of the phrase in the class; ``None`` places it after the other phrases.

        Raises
        ------
        KeyError
            If no class has the name.
        """
        class_index: int | None = self._vocabulary.index_of(class_name)
        class_item: QTreeWidgetItem | None = None if class_index is None else self.topLevelItem(class_index)
        if class_index is None or class_item is None:
            raise KeyError(f"No class named '{class_name}'.")
        phrase_count: int = len(self._vocabulary.classes[class_index].text_queries)
        phrase_item: QTreeWidgetItem = QTreeWidgetItem(["", "", ""])
        class_item.insertChild(phrase_count if position is None else min(position, phrase_count), phrase_item)
        class_item.setExpanded(True)
        self._edit_pending(phrase_item, text, self.NEW_PHRASE_PLACEHOLDER)

    def drop_query(
        self,
        query_item: QTreeWidgetItem,
        target_item: QTreeWidgetItem | None,
        indicator: QAbstractItemView.DropIndicatorPosition,
    ) -> None:
        """
        Move a query row to where it was dropped.

        Parameters
        ----------
        query_item : QTreeWidgetItem
            Dragged phrase or reference image row; class rows are ignored.
        target_item : QTreeWidgetItem | None
            Row under the drop point; ``None`` below the rows.
        indicator : QAbstractItemView.DropIndicatorPosition
            Whether the drop point is on, above or below ``target_item``, or on the empty viewport.
        """
        parent: QTreeWidgetItem | None = query_item.parent()
        if parent is None:
            return
        class_index: int = self.indexOfTopLevelItem(parent)
        child_index: int = parent.indexOfChild(query_item)
        target: QueryDropTarget = self._drop_target_of(target_item, indicator)
        try:
            if child_index < len(self._vocabulary.classes[class_index].text_queries):
                moved_position: tuple[int, int] = self._drop_phrase(class_index, child_index, target)
            else:
                moved_position = self._drop_reference_image(class_index, child_index, target)
        except ValueError as error:
            self.edit_rejected.emit(str(error))
            return
        self.populate()
        moved_item: QTreeWidgetItem | None = self._item_at(moved_position)
        if moved_item is not None:
            self.setCurrentItem(moved_item)
        self.classes_edited.emit()

    def populate(self) -> None:
        """
        Rebuild every row from the vocabulary and the reference board, keeping the current row where possible.

        A row being added and not yet confirmed is dropped.
        """
        current_position: tuple[int, int] | None = self._current_position()
        self._pending_item = None
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
        removed_images: list[tuple[str, ReferenceImage]] = []
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
                reference_images: tuple[ReferenceImage, ...] = self._board.reference_images_of(definition.name)
                removed_images.append((definition.name, reference_images[child_index - len(definition.text_queries)]))
        for class_name, reference_image in removed_images:
            self._board.remove_reference_image(class_name, reference_image)
        for class_index, phrase_indices in removed_phrases.items():
            self._vocabulary.remove_phrases(class_index, phrase_indices)
        self._vocabulary.remove_classes(removed_classes)
        self._board.retain_classes(self._vocabulary.class_names)
        self.clearSelection()
        self.populate()
        self.classes_edited.emit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.source() is not self:
            event.ignore()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.source() is not self:
            event.ignore()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        query_item: QTreeWidgetItem | None = self.currentItem()
        if event.source() is not self or query_item is None or query_item.parent() is None:
            event.ignore()
            return
        target_item: QTreeWidgetItem | None = self.itemAt(event.position().toPoint())
        indicator: QAbstractItemView.DropIndicatorPosition = self.dropIndicatorPosition()
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()
        QTimer.singleShot(0, partial(self.drop_query, query_item, target_item, indicator))

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self.itemAt(event.position().toPoint()) is None:
            self.start_new_class()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if Qt.Key(event.key()) in self.REMOVE_KEYS and self.selectedItems():
            self.remove_selected_rows()
            event.accept()
            return
        super().keyPressEvent(event)

    def _class_item_of(self, class_index: int, definition: ClassDefinition) -> QTreeWidgetItem:
        reference_images: tuple[ReferenceImage, ...] = self._board.reference_images_of(definition.name)
        used_image_count: int = len(reference_images) if self._is_image_prompt_supported else 0
        query_count: int = len(definition.text_queries) + used_image_count
        class_item: QTreeWidgetItem = QTreeWidgetItem([definition.name, str(class_index), str(query_count)])
        class_item.setIcon(self.NAME_COLUMN, self._palette.swatch_of(class_index))
        class_item.setFlags((class_item.flags() | Qt.ItemFlag.ItemIsEditable) & ~Qt.ItemFlag.ItemIsDragEnabled)
        class_item.setTextAlignment(self.ID_COLUMN, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        class_item.setTextAlignment(
            self.QUERY_COUNT_COLUMN, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        class_item.setToolTip(
            self.QUERY_COUNT_COLUMN,
            f"{len(definition.text_queries)} text prompt{'' if len(definition.text_queries) == 1 else 's'}, "
            + f"{used_image_count} reference image{'' if used_image_count == 1 else 's'}",
        )
        if query_count == 0:
            class_item.setForeground(self.NAME_COLUMN, QBrush(self.WARNING_COLOR))
            class_item.setToolTip(self.NAME_COLUMN, "No query the selected model can use; add a prompt.")
        for phrase in definition.text_queries:
            phrase_item: QTreeWidgetItem = QTreeWidgetItem([phrase, "", ""])
            phrase_item.setFlags((phrase_item.flags() | Qt.ItemFlag.ItemIsEditable) & ~Qt.ItemFlag.ItemIsDropEnabled)
            phrase_item.setToolTip(
                self.NAME_COLUMN,
                f"Text prompt for '{definition.name}'; double-click to edit, drag to move it to another class.",
            )
            class_item.addChild(phrase_item)
        for reference_image in reference_images:
            class_item.addChild(self._reference_item_of(definition.name, reference_image))
        return class_item

    def _reference_item_of(self, class_name: str, reference_image: ReferenceImage) -> QTreeWidgetItem:
        box_count: int = len(self._board.boxes_of(class_name, reference_image))
        reference_item: QTreeWidgetItem = QTreeWidgetItem(
            [f"{reference_image.name} ({box_count} box{'' if box_count == 1 else 'es'})", "", ""]
        )
        reference_item.setIcon(self.NAME_COLUMN, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        reference_item.setFlags(reference_item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
        if self._is_image_prompt_supported:
            reference_item.setToolTip(self.NAME_COLUMN, f"Reference image prompting '{class_name}'")
        else:
            reference_item.setForeground(self.NAME_COLUMN, QBrush(self.IGNORED_COLOR))
            reference_item.setToolTip(self.NAME_COLUMN, "Ignored: the selected backend does not take image prompts.")
        return reference_item

    def _selected_item(self) -> QTreeWidgetItem | None:
        current_item: QTreeWidgetItem | None = self.currentItem()
        if current_item is not None and current_item.isSelected():
            return current_item
        selected_items: list[QTreeWidgetItem] = self.selectedItems()
        return selected_items[0] if selected_items else None

    def _drop_target_of(
        self, target_item: QTreeWidgetItem | None, indicator: QAbstractItemView.DropIndicatorPosition
    ) -> QueryDropTarget:
        if target_item is None or indicator == QAbstractItemView.DropIndicatorPosition.OnViewport:
            return QueryDropTarget(kind=QueryDropKind.NEW_CLASS, class_index=len(self._vocabulary), position=0)
        parent: QTreeWidgetItem | None = target_item.parent()
        if parent is not None:
            class_index: int = self.indexOfTopLevelItem(parent)
            child_index: int = parent.indexOfChild(target_item)
            is_above: bool = indicator == QAbstractItemView.DropIndicatorPosition.AboveItem
            position: int = min(child_index if is_above else child_index + 1, self._phrase_count(class_index))
            return QueryDropTarget(kind=QueryDropKind.INTO_CLASS, class_index=class_index, position=position)
        class_index = self.indexOfTopLevelItem(target_item)
        match indicator:
            case QAbstractItemView.DropIndicatorPosition.AboveItem:
                return QueryDropTarget(kind=QueryDropKind.NEW_CLASS, class_index=class_index, position=0)
            case QAbstractItemView.DropIndicatorPosition.BelowItem if not (
                target_item.isExpanded() and target_item.childCount()
            ):
                return QueryDropTarget(kind=QueryDropKind.NEW_CLASS, class_index=class_index + 1, position=0)
            case QAbstractItemView.DropIndicatorPosition.BelowItem:
                return QueryDropTarget(kind=QueryDropKind.INTO_CLASS, class_index=class_index, position=0)
            case _:
                return QueryDropTarget(
                    kind=QueryDropKind.INTO_CLASS, class_index=class_index, position=self._phrase_count(class_index)
                )

    def _drop_phrase(self, class_index: int, phrase_index: int, target: QueryDropTarget) -> tuple[int, int]:
        match target.kind:
            case QueryDropKind.INTO_CLASS:
                self._vocabulary.move_phrase(class_index, phrase_index, target.class_index, target.position)
                is_shifted: bool = target.class_index == class_index and target.position > phrase_index
                self._expanded_class_names.add(self._vocabulary.class_names[target.class_index])
                return (target.class_index, target.position - 1 if is_shifted else target.position)
            case QueryDropKind.NEW_CLASS:
                return (self._vocabulary.promote_phrase(class_index, phrase_index, target.class_index), -1)

    def _drop_reference_image(self, class_index: int, child_index: int, target: QueryDropTarget) -> tuple[int, int]:
        match target.kind:
            case QueryDropKind.NEW_CLASS:
                raise ValueError("A reference image cannot become a class; drop it on a class instead.")
            case QueryDropKind.INTO_CLASS:
                class_name: str = self._vocabulary.class_names[class_index]
                reference_image: ReferenceImage = self._board.reference_images_of(class_name)[
                    child_index - self._phrase_count(class_index)
                ]
                target_name: str = self._vocabulary.class_names[target.class_index]
                self._board.move_reference_image(class_name, reference_image, target_name)
                self._expanded_class_names.add(target_name)
                image_position: int = self._board.reference_images_of(target_name).index(reference_image)
                return (target.class_index, self._phrase_count(target.class_index) + image_position)

    def _phrase_count(self, class_index: int) -> int:
        return len(self._vocabulary.classes[class_index].text_queries)

    def _current_position(self) -> tuple[int, int] | None:
        item: QTreeWidgetItem | None = self.currentItem()
        if item is None:
            return None
        parent: QTreeWidgetItem | None = item.parent()
        if parent is None:
            return (self.indexOfTopLevelItem(item), -1)
        return (self.indexOfTopLevelItem(parent), parent.indexOfChild(item))

    def _restore_current(self, position: tuple[int, int] | None) -> None:
        item: QTreeWidgetItem | None = None if position is None else self._item_at(position)
        if item is not None:
            self.setCurrentItem(item, 0, QItemSelectionModel.SelectionFlag.NoUpdate)

    def _item_at(self, position: tuple[int, int]) -> QTreeWidgetItem | None:
        class_index, child_index = position
        class_item: QTreeWidgetItem | None = self.topLevelItem(min(class_index, self.topLevelItemCount() - 1))
        if class_item is None:
            return None
        child_item: QTreeWidgetItem | None = class_item.child(child_index) if child_index >= 0 else None
        return child_item or class_item

    def _on_expansion_changed(self, item: QTreeWidgetItem, is_expanded: bool) -> None:
        if self._is_populating or item.parent() is not None:
            return
        class_name: str = item.text(self.NAME_COLUMN)
        if is_expanded:
            self._expanded_class_names.add(class_name)
        else:
            self._expanded_class_names.discard(class_name)

    def _edit_pending(self, item: QTreeWidgetItem, text: str, placeholder_text: str) -> None:
        self._pending_item = item
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        item.setText(self.NAME_COLUMN, text)
        self.scrollToItem(item)
        self.setCurrentItem(item)
        self._delegate.placeholder_text = placeholder_text
        self.editItem(item, self.NAME_COLUMN)
        self._delegate.placeholder_text = ""

    def _on_editor_closed(self, editor: QWidget, hint: QAbstractItemDelegate.EndEditHint) -> None:
        item: QTreeWidgetItem | None = self._pending_item
        if item is None:
            return
        self._pending_item = None
        parent: QTreeWidgetItem | None = item.parent()
        class_index: int | None = None if parent is None else self.indexOfTopLevelItem(parent)
        position: int = self.indexOfTopLevelItem(item) if parent is None else parent.indexOfChild(item)
        text: str = item.text(self.NAME_COLUMN)
        QTimer.singleShot(0, partial(self._finish_new_row, class_index, position, text, hint))

    def _finish_new_row(
        self, class_index: int | None, position: int, text: str, hint: QAbstractItemDelegate.EndEditHint
    ) -> None:
        if hint == QAbstractItemDelegate.EndEditHint.RevertModelCache or not text.strip():
            self.populate()
            return
        try:
            added_item_position: tuple[int, int] = (
                self._add_class(position, text)
                if class_index is None
                else self._add_phrases(class_index, position, text)
            )
        except ValueError as error:
            self.edit_rejected.emit(str(error))
            self.populate()
            if hint == QAbstractItemDelegate.EndEditHint.SubmitModelCache:
                self._reopen_new_row(class_index, position, text)
            return
        self.populate()
        added_item: QTreeWidgetItem | None = self._item_at(added_item_position)
        if added_item is not None:
            self.setCurrentItem(added_item)
        self.classes_edited.emit()

    def _add_class(self, position: int, text: str) -> tuple[int, int]:
        definition: ClassDefinition = ClassDefinition.parse(text)
        self._vocabulary.insert(position, definition)
        if not definition.is_named_query:
            self._expanded_class_names.add(definition.name)
        return (min(position, len(self._vocabulary) - 1), -1)

    def _add_phrases(self, class_index: int, position: int, text: str) -> tuple[int, int]:
        self._vocabulary.insert_phrases(class_index, position, ClassDefinition.split_phrases(text))
        self._expanded_class_names.add(self._vocabulary.class_names[class_index])
        return (class_index, min(position, self._phrase_count(class_index) - 1))

    def _reopen_new_row(self, class_index: int | None, position: int, text: str) -> None:
        if class_index is None:
            self.start_new_class(text, position)
        else:
            self.start_new_phrase(self._vocabulary.class_names[class_index], text, position)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._is_populating or column != self.NAME_COLUMN or item is self._pending_item:
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
