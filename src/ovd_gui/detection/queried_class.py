from dataclasses import dataclass, replace

from .reference_box import ReferenceBox


@dataclass(frozen=True)
class QueriedClass:
    """
    One class as a prompt queries it: its phrases and the reference boxes of its visual queries.

    Two queried classes are equal when they query the same phrases and boxes, regardless of order, so a result can
    tell whether the class it was detected with has been edited since.

    Attributes
    ----------
    name : str
        Class name.
    phrases : frozenset[str]
        Phrases of its text queries.
    reference_boxes : frozenset[ReferenceBox]
        Boxes of its visual queries; empty when the model does not take image prompts.
    """

    name: str
    phrases: frozenset[str]
    reference_boxes: frozenset[ReferenceBox]

    @property
    def is_queryable(self) -> bool:
        """
        Whether the class has any query.

        Returns
        -------
        bool
            True with at least one phrase or reference box.
        """
        return bool(self.phrases or self.reference_boxes)

    def without_reference_boxes(self) -> "QueriedClass":
        """
        Same class queried by its phrases only, as a model without image prompts reads it.

        Returns
        -------
        QueriedClass
            Copy without reference boxes.
        """
        return replace(self, reference_boxes=frozenset())
