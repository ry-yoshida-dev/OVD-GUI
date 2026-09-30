from pydantic import BaseModel


class PhraseReference(BaseModel):
    """
    One phrase of a class.

    Attributes
    ----------
    class_index : int
        Class id.
    phrase_index : int
        Position of the phrase in the class.
    """

    class_index: int
    phrase_index: int
