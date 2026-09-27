from collections.abc import Iterable

from .class_definition import ClassDefinition


class ClassVocabulary:
    """
    Ordered classes to detect, the index being the class id.

    Class names are unique regardless of case, and so are phrases across all classes, since a phrase can report
    only one class. Interactive edits that would break either rule raise ``ValueError`` and change nothing;
    ``replace`` instead drops the offending classes and phrases, which suits lists read from files.
    """

    def __init__(self) -> None:
        self._classes: list[ClassDefinition] = []

    def __len__(self) -> int:
        return len(self._classes)

    @property
    def classes(self) -> tuple[ClassDefinition, ...]:
        """
        Classes in class-id order.

        Returns
        -------
        tuple[ClassDefinition, ...]
            Every class.
        """
        return tuple(self._classes)

    @property
    def class_names(self) -> tuple[str, ...]:
        """
        Class names in class-id order.

        Returns
        -------
        tuple[str, ...]
            Name of every class.
        """
        return tuple(definition.name for definition in self._classes)

    def index_of(self, class_name: str) -> int | None:
        """
        Class id of a name, compared regardless of case.

        Parameters
        ----------
        class_name : str
            Name to look up.

        Returns
        -------
        int | None
            ``None`` when no class has the name.
        """
        key: str = ClassDefinition.normalize(class_name).casefold()
        for index, definition in enumerate(self._classes):
            if definition.name.casefold() == key:
                return index
        return None

    def replace(self, definitions: Iterable[ClassDefinition]) -> None:
        """
        Replace every class, dropping repeated names and phrases already used by an earlier class.

        Parameters
        ----------
        definitions : Iterable[ClassDefinition]
            Classes in class-id order.
        """
        self._classes = []
        for definition in definitions:
            if self.index_of(definition.name) is not None:
                continue
            used_phrases: frozenset[str] = self._used_phrases()
            self._classes.append(
                definition.with_text_queries(
                    tuple(phrase for phrase in definition.text_queries if phrase.casefold() not in used_phrases)
                )
            )

    def add(self, definition: ClassDefinition) -> int:
        """
        Append a class, or add its phrases to the class of the same name.

        Parameters
        ----------
        definition : ClassDefinition
            Class to add.

        Returns
        -------
        int
            Class id of the added or extended class.

        Raises
        ------
        ValueError
            If a phrase is already a prompt of another class.
        """
        index: int | None = self.index_of(definition.name)
        if index is None:
            self.insert(len(self._classes), definition)
            return len(self._classes) - 1
        self.add_phrases(index, definition.text_queries)
        return index

    def insert(self, position: int, definition: ClassDefinition) -> None:
        """
        Insert a new class; it and the classes after it are renumbered.

        Parameters
        ----------
        position : int
            Class id of the new class; clamped to the end.
        definition : ClassDefinition
            Class to insert.

        Raises
        ------
        ValueError
            If a class of the same name exists or a phrase is already a prompt of another class.
        """
        if self.index_of(definition.name) is not None:
            raise ValueError(f"A class named '{definition.name}' already exists.")
        self._check_phrases_are_free(definition.text_queries, ignored_index=None)
        self._classes.insert(position, definition)

    def add_phrases(self, index: int, phrases: Iterable[str]) -> None:
        """
        Append phrases to one class, skipping those it already has.

        Parameters
        ----------
        index : int
            Class id.
        phrases : Iterable[str]
            Phrases to add.

        Raises
        ------
        ValueError
            If a phrase is invalid or is already a prompt of another class.
        """
        self.insert_phrases(index, len(self._classes[index].text_queries), phrases)

    def insert_phrases(self, index: int, position: int, phrases: Iterable[str]) -> None:
        """
        Insert phrases into one class at a position, skipping those it already has.

        Parameters
        ----------
        index : int
            Class id.
        position : int
            Position of the first new phrase within the class; clamped to the end.
        phrases : Iterable[str]
            Phrases to add.

        Raises
        ------
        ValueError
            If a phrase is invalid or is already a prompt of another class.
        """
        definition: ClassDefinition = self._classes[index]
        own_phrases: set[str] = {phrase.casefold() for phrase in definition.text_queries}
        new_phrases: list[str] = []
        for raw_phrase in phrases:
            phrase: str = ClassDefinition.normalize(raw_phrase)
            if phrase.casefold() not in own_phrases:
                own_phrases.add(phrase.casefold())
                new_phrases.append(phrase)
        self._check_phrases_are_free(new_phrases, ignored_index=index)
        phrases_before: tuple[str, ...] = definition.text_queries[:position]
        phrases_after: tuple[str, ...] = definition.text_queries[position:]
        self._classes[index] = definition.with_text_queries((*phrases_before, *new_phrases, *phrases_after))

    def move_phrase(self, index: int, phrase_index: int, target_index: int, position: int) -> None:
        """
        Move one phrase to a position in the same or another class.

        Parameters
        ----------
        index : int
            Class id the phrase belongs to.
        phrase_index : int
            Position of the phrase in its class.
        target_index : int
            Class id to move the phrase to.
        position : int
            Position of the phrase in the target class, counted before the phrase is taken out.
        """
        phrase: str = self._classes[index].text_queries[phrase_index]
        self.remove_phrases(index, (phrase_index,))
        if index == target_index and position > phrase_index:
            position -= 1
        self.insert_phrases(target_index, position, (phrase,))

    def promote_phrase(self, index: int, phrase_index: int, position: int) -> int:
        """
        Turn one phrase into a class of its own, queried by the phrase.

        Parameters
        ----------
        index : int
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
            If a class is already named like the phrase; nothing changes then.
        """
        phrase: str = self._classes[index].text_queries[phrase_index]
        if self.index_of(phrase) is not None:
            raise ValueError(f"A class named '{phrase}' already exists.")
        self.remove_phrases(index, (phrase_index,))
        self.insert(position, ClassDefinition.named(phrase))
        return min(position, len(self._classes) - 1)

    def rename_class(self, index: int, name: str) -> ClassDefinition:
        """
        Rename one class; a class queried by its name follows the new name.

        Parameters
        ----------
        index : int
            Class id.
        name : str
            New name.

        Returns
        -------
        ClassDefinition
            The class before renaming.

        Raises
        ------
        ValueError
            If the name is invalid or used by another class, or the new phrase queries another class.
        """
        previous: ClassDefinition = self._classes[index]
        renamed: ClassDefinition = previous.renamed(name)
        other_index: int | None = self.index_of(renamed.name)
        if other_index is not None and other_index != index:
            raise ValueError(f"A class named '{renamed.name}' already exists.")
        self._check_phrases_are_free(renamed.text_queries, ignored_index=index)
        self._classes[index] = renamed
        return previous

    def rename_phrase(self, index: int, phrase_index: int, phrase: str) -> None:
        """
        Replace one phrase of a class.

        Parameters
        ----------
        index : int
            Class id.
        phrase_index : int
            Position of the phrase in the class.
        phrase : str
            New phrase.

        Raises
        ------
        ValueError
            If the phrase is invalid, repeats another phrase of the class, or queries another class.
        """
        definition: ClassDefinition = self._classes[index]
        phrases: list[str] = list(definition.text_queries)
        phrases[phrase_index] = phrase
        updated: ClassDefinition = definition.with_text_queries(tuple(phrases))
        self._check_phrases_are_free(updated.text_queries, ignored_index=index)
        self._classes[index] = updated

    def remove_classes(self, indices: Iterable[int]) -> None:
        """
        Remove classes; later classes move up.

        Parameters
        ----------
        indices : Iterable[int]
            Class ids to remove; unknown ids are ignored.
        """
        removed: frozenset[int] = frozenset(indices)
        self._classes = [definition for index, definition in enumerate(self._classes) if index not in removed]

    def remove_phrases(self, index: int, phrase_indices: Iterable[int]) -> None:
        """
        Remove phrases of one class.

        Parameters
        ----------
        index : int
            Class id.
        phrase_indices : Iterable[int]
            Positions of the phrases to remove; unknown positions are ignored.
        """
        removed: frozenset[int] = frozenset(phrase_indices)
        definition: ClassDefinition = self._classes[index]
        self._classes[index] = definition.with_text_queries(
            tuple(phrase for position, phrase in enumerate(definition.text_queries) if position not in removed)
        )

    def _used_phrases(self, ignored_index: int | None = None) -> frozenset[str]:
        return frozenset(
            phrase.casefold()
            for index, definition in enumerate(self._classes)
            if index != ignored_index
            for phrase in definition.text_queries
        )

    def _check_phrases_are_free(self, phrases: Iterable[str], ignored_index: int | None) -> None:
        used_phrases: frozenset[str] = self._used_phrases(ignored_index)
        for phrase in phrases:
            if phrase.casefold() in used_phrases:
                owner: str = next(
                    definition.name
                    for definition in self._classes
                    if phrase.casefold() in {text_query.casefold() for text_query in definition.text_queries}
                )
                raise ValueError(f"'{phrase}' is already a prompt of the class '{owner}'.")
