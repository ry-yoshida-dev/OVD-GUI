from dataclasses import dataclass

from ..detection import LabeledPrompt


@dataclass(frozen=True)
class PromptPreparation:
    """
    Prompt built from the current classes, or why none could be built.

    Attributes
    ----------
    labeled_prompt : LabeledPrompt | None
        Prompt to detect with; ``None`` when it could not be built.
    issue : str
        Why no prompt could be built; empty when one was built or approval is needed.
    unapproved_class_names : tuple[str, ...]
        Reference-only classes the selected model cannot query, which the user has to approve leaving out.
    """

    labeled_prompt: LabeledPrompt | None
    issue: str = ""
    unapproved_class_names: tuple[str, ...] = ()
