from dataclasses import dataclass

from .prompt_signature import PromptSignature
from .queried_class import QueriedClass


@dataclass(frozen=True)
class PromptChange:
    """
    How the classes have changed since a result was detected.

    An added class may be missing from the result, a removed class is still reported by it, and the detections of an
    edited class came from other phrases or reference boxes; the detections of every other class are still current.

    Attributes
    ----------
    added_class_names : tuple[str, ...]
        Classes queried now but not by the result's prompt, in current class order.
    removed_class_names : tuple[str, ...]
        Classes the result's prompt queried that are no longer queried, in the result's class order.
    edited_class_names : tuple[str, ...]
        Classes queried by both whose phrases or reference boxes differ, in current class order.
    """

    added_class_names: tuple[str, ...]
    removed_class_names: tuple[str, ...]
    edited_class_names: tuple[str, ...]

    @classmethod
    def between(cls, recorded: PromptSignature, current: PromptSignature) -> "PromptChange":
        """
        Compare the prompt of a result with the current one.

        Parameters
        ----------
        recorded : PromptSignature
            Prompt the result was detected with.
        current : PromptSignature
            Prompt a detection would use now.

        Returns
        -------
        PromptChange
            Added, removed and edited classes; unchanged when both query the same.
        """
        added_class_names: list[str] = []
        edited_class_names: list[str] = []
        for queried_class in current.classes:
            recorded_class: QueriedClass | None = recorded.class_named(queried_class.name)
            if recorded_class is None:
                added_class_names.append(queried_class.name)
            elif recorded_class != queried_class:
                edited_class_names.append(queried_class.name)
        removed_class_names: tuple[str, ...] = tuple(
            recorded_class.name
            for recorded_class in recorded.classes
            if current.class_named(recorded_class.name) is None
        )
        return cls(
            added_class_names=tuple(added_class_names),
            removed_class_names=removed_class_names,
            edited_class_names=tuple(edited_class_names),
        )

    @property
    def is_unchanged(self) -> bool:
        """
        Whether the result's prompt queries the same as the current one.

        Returns
        -------
        bool
            True without any added, removed or edited class.
        """
        return not (self.added_class_names or self.removed_class_names or self.edited_class_names)

    @property
    def description(self) -> str:
        """
        One line naming the changed classes.

        Returns
        -------
        str
            E.g. ``"added car · removed person · edited dog"``; empty when unchanged.
        """
        parts: list[str] = [
            f"{verb} {', '.join(names)}"
            for verb, names in (
                ("added", self.added_class_names),
                ("removed", self.removed_class_names),
                ("edited", self.edited_class_names),
            )
            if names
        ]
        return " · ".join(parts)
