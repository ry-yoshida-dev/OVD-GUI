from pydantic import BaseModel

from .image_prompt_reference import ImagePromptReference
from .phrase_reference import PhraseReference


class RemoveClassesBody(BaseModel):
    """
    Classes, phrases and reference images to remove at once.

    Attributes
    ----------
    class_indices : list[int]
        Class ids of the classes to remove.
    phrases : list[PhraseReference]
        Phrases to remove.
    references : list[ImagePromptReference]
        Reference images to remove.
    """

    class_indices: list[int] = []
    phrases: list[PhraseReference] = []
    references: list[ImagePromptReference] = []
