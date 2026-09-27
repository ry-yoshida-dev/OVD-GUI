from dataclasses import dataclass, replace
from typing import ClassVar


@dataclass(frozen=True)
class ClassDefinition:
    """
    Output class and the text phrases querying it, written ``car: car, suv, taxi``.

    Detections are reported under ``name``; the model reads ``text_queries``. A class named ``car`` with no colon
    in its text is queried by its own name. Runs of whitespace are collapsed to one space.

    Attributes
    ----------
    name : str
        Output label; must not contain ``:`` or ``,``.
    text_queries : tuple[str, ...]
        Phrases the model reads, unique regardless of case; must not contain ``,``. Empty for a class queried only
        by reference images.

    Raises
    ------
    ValueError
        If the name or a phrase is blank, contains a separator, or phrases repeat.
    """

    QUERY_SEPARATOR: ClassVar[str] = ":"
    PHRASE_SEPARATOR: ClassVar[str] = ","

    name: str
    text_queries: tuple[str, ...]

    def __post_init__(self) -> None:
        name: str = self.normalize(self.name)
        if not name:
            raise ValueError("Class name must not be blank.")
        if self.QUERY_SEPARATOR in name or self.PHRASE_SEPARATOR in name:
            raise ValueError(
                f"Class name must not contain '{self.QUERY_SEPARATOR}' or '{self.PHRASE_SEPARATOR}': {name!r}"
            )
        text_queries: tuple[str, ...] = tuple(self.normalize(text_query) for text_query in self.text_queries)
        if any(not text_query for text_query in text_queries):
            raise ValueError(f"Phrases of '{name}' must not be blank.")
        if any(self.PHRASE_SEPARATOR in text_query for text_query in text_queries):
            raise ValueError(f"Phrases of '{name}' must not contain '{self.PHRASE_SEPARATOR}'.")
        if len({text_query.casefold() for text_query in text_queries}) != len(text_queries):
            raise ValueError(f"Phrases of '{name}' must be unique: {', '.join(text_queries)}")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "text_queries", text_queries)

    @classmethod
    def named(cls, name: str) -> "ClassDefinition":
        """
        Class queried by its own name.

        Parameters
        ----------
        name : str
            Class name.

        Returns
        -------
        ClassDefinition
            Class whose only phrase is ``name``.
        """
        return cls(name=name, text_queries=(name,))

    @classmethod
    def parse(cls, text: str) -> "ClassDefinition":
        """
        Read ``name`` or ``name: phrase, phrase``.

        Parameters
        ----------
        text : str
            One class written as in a class list file.

        Returns
        -------
        ClassDefinition
            Class queried by the listed phrases, or by its name when there is no colon.

        Raises
        ------
        ValueError
            If the name or a phrase is invalid.
        """
        name, separator, phrases = text.partition(cls.QUERY_SEPARATOR)
        if not separator:
            return cls.named(name)
        return cls(name=name, text_queries=cls.split_phrases(phrases))

    @classmethod
    def split_phrases(cls, text: str) -> tuple[str, ...]:
        """
        Split comma-separated phrases, skipping blank ones.

        Parameters
        ----------
        text : str
            Phrases separated by ``,``.

        Returns
        -------
        tuple[str, ...]
            Normalized non-blank phrases in order.
        """
        return tuple(phrase for raw_phrase in text.split(cls.PHRASE_SEPARATOR) if (phrase := cls.normalize(raw_phrase)))

    @staticmethod
    def normalize(text: str) -> str:
        """
        Collapse whitespace runs to one space and strip the ends.

        Parameters
        ----------
        text : str
            Raw name or phrase.

        Returns
        -------
        str
            Normalized text.
        """
        return " ".join(text.split())

    @property
    def is_named_query(self) -> bool:
        """
        Whether the class is queried by its own name only.

        Returns
        -------
        bool
            True when the only phrase is the name.
        """
        return self.text_queries == (self.name,)

    @property
    def text(self) -> str:
        """
        The class written as in a class list file.

        Returns
        -------
        str
            ``name`` when queried by its name only, ``name: phrase, phrase`` otherwise (``name:`` without phrases).
        """
        if self.is_named_query:
            return self.name
        phrases: str = f"{self.PHRASE_SEPARATOR} ".join(self.text_queries)
        return f"{self.name}{self.QUERY_SEPARATOR} {phrases}".rstrip()

    def renamed(self, name: str) -> "ClassDefinition":
        """
        Same class under another name; a class queried by its name is then queried by the new name.

        Parameters
        ----------
        name : str
            New class name.

        Returns
        -------
        ClassDefinition
            Renamed copy.
        """
        if self.is_named_query:
            return ClassDefinition.named(name)
        return replace(self, name=name)

    def with_text_queries(self, text_queries: tuple[str, ...]) -> "ClassDefinition":
        """
        Same class queried by other phrases.

        Parameters
        ----------
        text_queries : tuple[str, ...]
            New phrases.

        Returns
        -------
        ClassDefinition
            Copy with ``text_queries`` replaced.
        """
        return replace(self, text_queries=text_queries)
