from dataclasses import dataclass

from open_vocabulary_detector import PromptKind

from .queried_class import QueriedClass


@dataclass(frozen=True)
class PromptSignature:
    """
    What a prompt queries, class by class, independent of query order and of cached embeddings.

    Attributes
    ----------
    classes : tuple[QueriedClass, ...]
        Queried classes in class-id order.

    Raises
    ------
    ValueError
        If two classes share a name.
    """

    classes: tuple[QueriedClass, ...]

    def __post_init__(self) -> None:
        names: list[str] = [queried_class.name for queried_class in self.classes]
        if len(set(names)) != len(names):
            raise ValueError(f"class names must be unique. got {', '.join(names)}")

    def class_named(self, name: str) -> QueriedClass | None:
        """
        Look up one class.

        Parameters
        ----------
        name : str
            Class name.

        Returns
        -------
        QueriedClass | None
            ``None`` if the prompt does not query the class.
        """
        return next((queried_class for queried_class in self.classes if queried_class.name == name), None)

    def for_prompt_kinds(self, supported_kinds: frozenset[PromptKind]) -> "PromptSignature":
        """
        What a model accepting some query kinds would be queried with.

        Parameters
        ----------
        supported_kinds : frozenset[PromptKind]
            Query kinds the model accepts; reference boxes are dropped without ``VISUAL``.

        Returns
        -------
        PromptSignature
            Signature without the queries the model cannot take and without classes left with no query.
        """
        is_visual_supported: bool = PromptKind.VISUAL in supported_kinds
        usable_classes: tuple[QueriedClass, ...] = tuple(
            queried_class if is_visual_supported else queried_class.without_reference_boxes()
            for queried_class in self.classes
        )
        return PromptSignature(tuple(queried_class for queried_class in usable_classes if queried_class.is_queryable))
