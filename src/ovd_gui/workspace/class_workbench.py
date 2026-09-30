from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from PIL import Image

from ..detection import ReferenceBoard, ReferenceBox, ReferenceImage
from ..storage import ClassSet, ClassSetArchive, ClassSetStore
from ..vocabulary import ClassDefinition, ClassListFile, ClassVocabulary


class ClassWorkbench:
    """
    Classes to detect with their phrases and reference images, edited by class id, and the class set they belong to.

    Edits that would break the vocabulary rules raise ``ValueError`` and change nothing. Reference boxes follow their
    class when it is renamed and are dropped with it. The workbench remembers the saved class set the classes were
    last loaded from or saved to, and whether they were edited since.
    """

    def __init__(self, class_set_store: ClassSetStore) -> None:
        """
        Parameters
        ----------
        class_set_store : ClassSetStore
            Saved class sets.
        """
        self._class_set_store: ClassSetStore = class_set_store
        self._vocabulary: ClassVocabulary = ClassVocabulary()
        self._board: ReferenceBoard = ReferenceBoard()
        self._class_set_name: str = ""
        self._is_edited: bool = False

    @property
    def classes(self) -> tuple[ClassDefinition, ...]:
        """
        Classes in class-id order.

        Returns
        -------
        tuple[ClassDefinition, ...]
            Every class.
        """
        return self._vocabulary.classes

    @property
    def class_names(self) -> tuple[str, ...]:
        """
        Class names in class-id order.

        Returns
        -------
        tuple[str, ...]
            Name of every class.
        """
        return self._vocabulary.class_names

    @property
    def reference_board(self) -> ReferenceBoard:
        """
        Reference boxes of the classes.

        Returns
        -------
        ReferenceBoard
            Board holding every reference box and image.
        """
        return self._board

    @property
    def class_set_store(self) -> ClassSetStore:
        """
        Saved class sets.

        Returns
        -------
        ClassSetStore
            Store given at construction.
        """
        return self._class_set_store

    @property
    def class_set_name(self) -> str:
        """
        Saved class set the classes were last loaded from or saved to.

        Returns
        -------
        str
            Set name; empty for classes not tied to a saved set or when the set no longer exists.
        """
        if self._class_set_name and not self._class_set_store.has_class_set(self._class_set_name):
            return ""
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

    @property
    def is_unsaved(self) -> bool:
        """
        Whether replacing the classes would lose work.

        Returns
        -------
        bool
            True when classes exist and are edited or not tied to a saved set.
        """
        return bool(self.classes) and (self._is_edited or not self.class_set_name)

    def restore(self, definitions: Iterable[ClassDefinition]) -> None:
        """
        Replace every class, e.g. with the classes of the last run, without marking them edited.

        Parameters
        ----------
        definitions : Iterable[ClassDefinition]
            Classes in class-id order.
        """
        self._replace(definitions)
        self._associate("")

    def set_classes(self, definitions: Iterable[ClassDefinition]) -> None:
        """
        Replace every class, keeping the reference images of the classes still listed.

        Parameters
        ----------
        definitions : Iterable[ClassDefinition]
            Classes in class-id order; repeated names and phrases already used by an earlier class are dropped.
        """
        self._replace(definitions)
        self._is_edited = True

    def add_class(self, position: int, text: str) -> int:
        """
        Insert a class written ``name`` or ``name: phrase, phrase``.

        Parameters
        ----------
        position : int
            Class id of the new class; clamped to the end.
        text : str
            Class as written in a class list file.

        Returns
        -------
        int
            Class id of the new class.

        Raises
        ------
        ValueError
            If the class is invalid, its name is taken or a phrase queries another class.
        """
        self._vocabulary.insert(position, ClassDefinition.parse(text))
        self._is_edited = True
        return min(position, len(self._vocabulary) - 1)

    def add_phrases(self, class_index: int, position: int, text: str) -> None:
        """
        Insert comma-separated phrases into one class.

        Parameters
        ----------
        class_index : int
            Class id.
        position : int
            Position of the first new phrase within the class; clamped to the end.
        text : str
            Phrases separated by ``,``.

        Raises
        ------
        ValueError
            If no phrase is given, or a phrase is invalid or queries another class.
        IndexError
            If the class does not exist.
        """
        phrases: tuple[str, ...] = ClassDefinition.split_phrases(text)
        if not phrases:
            raise ValueError("Type at least one phrase.")
        self._require_class(class_index)
        self._vocabulary.insert_phrases(class_index, position, phrases)
        self._is_edited = True

    def rename_class(self, class_index: int, name: str) -> None:
        """
        Rename one class; its reference images follow.

        Parameters
        ----------
        class_index : int
            Class id.
        name : str
            New name.

        Raises
        ------
        ValueError
            If the name is invalid or taken.
        IndexError
            If the class does not exist.
        """
        self._require_class(class_index)
        previous: ClassDefinition = self._vocabulary.rename_class(class_index, name)
        self._board.rename_class(previous.name, self._vocabulary.class_names[class_index])
        self._is_edited = True

    def rename_phrase(self, class_index: int, phrase_index: int, phrase: str) -> None:
        """
        Replace one phrase of a class.

        Parameters
        ----------
        class_index : int
            Class id.
        phrase_index : int
            Position of the phrase in the class.
        phrase : str
            New phrase.

        Raises
        ------
        ValueError
            If the phrase is invalid or queries another class.
        IndexError
            If the class or phrase does not exist.
        """
        self._require_phrase(class_index, phrase_index)
        self._vocabulary.rename_phrase(class_index, phrase_index, phrase)
        self._is_edited = True

    def remove(
        self,
        class_indices: Iterable[int],
        phrase_indices: Mapping[int, Iterable[int]],
        reference_images: Sequence[tuple[int, ReferenceImage]],
    ) -> None:
        """
        Remove classes, phrases and reference images at once.

        Parameters
        ----------
        class_indices : Iterable[int]
            Class ids of the classes to remove.
        phrase_indices : Mapping[int, Iterable[int]]
            Positions of the phrases to remove, per class id.
        reference_images : Sequence[tuple[int, ReferenceImage]]
            Class id and reference image of each visual query to remove.
        """
        class_names: tuple[str, ...] = self.class_names
        for class_index, reference_image in reference_images:
            if 0 <= class_index < len(class_names):
                self._board.remove_reference_image(class_names[class_index], reference_image)
        for class_index, positions in phrase_indices.items():
            if 0 <= class_index < len(class_names):
                self._vocabulary.remove_phrases(class_index, positions)
        self._vocabulary.remove_classes(class_indices)
        self._board.retain_classes(self._vocabulary.class_names)
        self._is_edited = True

    def move_phrase(self, class_index: int, phrase_index: int, target_class_index: int, position: int) -> None:
        """
        Move one phrase to a position in the same or another class.

        Parameters
        ----------
        class_index : int
            Class id the phrase belongs to.
        phrase_index : int
            Position of the phrase in its class.
        target_class_index : int
            Class id to move the phrase to.
        position : int
            Position in the target class, counted before the phrase is taken out.

        Raises
        ------
        IndexError
            If a class or the phrase does not exist.
        """
        self._require_phrase(class_index, phrase_index)
        self._require_class(target_class_index)
        self._vocabulary.move_phrase(class_index, phrase_index, target_class_index, position)
        self._is_edited = True

    def promote_phrase(self, class_index: int, phrase_index: int, position: int) -> int:
        """
        Turn one phrase into a class of its own.

        Parameters
        ----------
        class_index : int
            Class id the phrase belongs to.
        phrase_index : int
            Position of the phrase in its class.
        position : int
            Class id of the new class; clamped to the end.

        Returns
        -------
        int
            Class id of the new class.

        Raises
        ------
        ValueError
            If a class is already named like the phrase.
        IndexError
            If the class or phrase does not exist.
        """
        self._require_phrase(class_index, phrase_index)
        new_index: int = self._vocabulary.promote_phrase(class_index, phrase_index, position)
        self._is_edited = True
        return new_index

    def move_reference_image(self, class_index: int, reference_image: ReferenceImage, target_class_index: int) -> None:
        """
        Move the boxes of one class on one reference image to another class.

        Parameters
        ----------
        class_index : int
            Class id the boxes belong to.
        reference_image : ReferenceImage
            Reference image of the boxes.
        target_class_index : int
            Class id to move the boxes to.

        Raises
        ------
        IndexError
            If a class does not exist.
        """
        self._require_class(class_index)
        self._require_class(target_class_index)
        class_names: tuple[str, ...] = self.class_names
        self._board.move_reference_image(class_names[class_index], reference_image, class_names[target_class_index])
        self._is_edited = True

    def add_reference_boxes(self, boxes: Sequence[ReferenceBox], image: Image.Image) -> None:
        """
        Add boxes drawn on one reference image.

        Parameters
        ----------
        boxes : Sequence[ReferenceBox]
            Boxes of existing classes on ``image``.
        image : Image.Image
            RGB pixels of the reference image.

        Raises
        ------
        ValueError
            If no box is given, a box lies outside the image or belongs to no class.
        """
        if not boxes:
            raise ValueError("Draw at least one box or use the whole image.")
        for box in boxes:
            if box.class_name not in self.class_names:
                raise ValueError(f"No class named '{box.class_name}'.")
        for box in boxes:
            self._board.add(box, image)
        self._is_edited = True

    def save_class_set(self, name: str) -> None:
        """
        Save the classes, phrases and reference images as a named class set, replacing one of the same name.

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

    def load_file(self, path: Path, display_name: str) -> None:
        """
        Replace every class with the classes of a file.

        A class set archive also replaces every reference image; a class list text file keeps the reference images of
        the classes it lists.

        Parameters
        ----------
        path : Path
            Class set archive (``.ovdset``) or text file listing one class per line.
        display_name : str
            Name of the file for messages.

        Raises
        ------
        OSError
            If the file cannot be read.
        ValueError
            If the file content is invalid or the file lists no class.
        """
        if ClassSetArchive.is_archive_path(path):
            self._apply_class_set(ClassSetArchive(path).read(), display_name)
        else:
            definitions: tuple[ClassDefinition, ...] = ClassListFile(path).read()
            if not definitions:
                raise ValueError(f"No classes found in {display_name}.")
            self._replace(definitions)
        self._associate("")

    def rename_class_set(self, name: str, new_name: str) -> None:
        """
        Rename a saved class set; the classes stay tied to it under its new name.

        Parameters
        ----------
        name : str
            Current set name.
        new_name : str
            New set name.

        Raises
        ------
        ValueError
            If a name is not usable or the new name is taken.
        OSError
            If the file cannot be renamed.
        """
        self._class_set_store.rename_class_set(name, new_name)
        if self._class_set_name == name.strip():
            self._class_set_name = new_name.strip()

    def _replace(self, definitions: Iterable[ClassDefinition]) -> None:
        self._vocabulary.replace(definitions)
        self._board.retain_classes(self._vocabulary.class_names)

    def _apply_class_set(self, class_set: ClassSet, source_name: str) -> None:
        if not class_set.classes:
            raise ValueError(f"Class set '{source_name}' lists no class.")
        self._board.replace(class_set.reference_boxes, class_set.reference_pixels)
        self._replace(class_set.classes)

    def _associate(self, name: str) -> None:
        self._class_set_name = name
        self._is_edited = False

    def _require_class(self, class_index: int) -> None:
        if not 0 <= class_index < len(self._vocabulary):
            raise IndexError(f"class index must be in [0, {len(self._vocabulary)}). got {class_index}")

    def _require_phrase(self, class_index: int, phrase_index: int) -> None:
        self._require_class(class_index)
        phrase_count: int = len(self._vocabulary.classes[class_index].text_queries)
        if not 0 <= phrase_index < phrase_count:
            raise IndexError(f"phrase index must be in [0, {phrase_count}). got {phrase_index}")
