from dataclasses import dataclass

from .query_drop_kind import QueryDropKind


@dataclass(frozen=True)
class QueryDropTarget:
    """
    Where a dragged query row lands in the class tree.

    Attributes
    ----------
    kind : QueryDropKind
        Whether the query joins a class or becomes a new class.
    class_index : int
        Class receiving the query, or class id of the new class.
    position : int
        Position of the phrase within the receiving class; unused for a new class.
    """

    kind: QueryDropKind
    class_index: int
    position: int
