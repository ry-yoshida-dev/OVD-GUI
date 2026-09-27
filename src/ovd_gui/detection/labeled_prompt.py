from dataclasses import dataclass

from open_vocabulary_detector import Prompt


@dataclass(frozen=True, eq=False)
class LabeledPrompt:
    """
    Prompt with a display label for each of its queries.

    Attributes
    ----------
    prompt : Prompt
        Prompt handed to the detector.
    query_labels : tuple[str, ...]
        Label of each query in query-id order: the phrase of a text query, the reference image name of a visual one.

    Raises
    ------
    ValueError
        If there is not exactly one label per query.
    """

    prompt: Prompt
    query_labels: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.query_labels) != len(self.prompt.queries):
            raise ValueError(f"expected {len(self.prompt.queries)} query labels. got {len(self.query_labels)}")
