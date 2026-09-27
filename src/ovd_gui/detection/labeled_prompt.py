from dataclasses import dataclass

from open_vocabulary_detector import Prompt

from .prompt_signature import PromptSignature


@dataclass(frozen=True, eq=False)
class LabeledPrompt:
    """
    Prompt with a display label for each of its queries and the signature of what it queries.

    Attributes
    ----------
    prompt : Prompt
        Prompt handed to the detector.
    query_labels : tuple[str, ...]
        Label of each query in query-id order: the phrase of a text query, the reference image name of a visual one.
    signature : PromptSignature
        Phrases and reference boxes of every class, telling later whether the classes have changed since.

    Raises
    ------
    ValueError
        If there is not exactly one label per query, or the signature does not query the classes of the prompt.
    """

    prompt: Prompt
    query_labels: tuple[str, ...]
    signature: PromptSignature

    def __post_init__(self) -> None:
        if len(self.query_labels) != len(self.prompt.queries):
            raise ValueError(f"expected {len(self.prompt.queries)} query labels. got {len(self.query_labels)}")
        signature_names: tuple[str, ...] = tuple(queried_class.name for queried_class in self.signature.classes)
        if signature_names != self.prompt.class_names:
            raise ValueError(f"signature must query {self.prompt.class_names}. got {signature_names}")
