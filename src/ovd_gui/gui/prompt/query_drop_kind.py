from enum import Enum


class QueryDropKind(Enum):
    """
    What dropping a dragged query row does.

    Attributes
    ----------
    INTO_CLASS
        The query moves into a class, next to its other queries.
    NEW_CLASS
        The phrase becomes a class of its own, queried by the phrase.
    """

    INTO_CLASS = "into_class"
    NEW_CLASS = "new_class"
