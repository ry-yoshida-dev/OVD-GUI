from pydantic import BaseModel


class MovePhraseBody(BaseModel):
    """
    Phrase dragged to another place.

    Attributes
    ----------
    class_index : int
        Class id the phrase belongs to.
    phrase_index : int
        Position of the phrase in its class.
    target_class_index : int | None
        Class receiving the phrase; ``None`` to make the phrase a class of its own.
    position : int
        Position in the target class, counted before the phrase is taken out, or class id of the new class.
    """

    class_index: int
    phrase_index: int
    target_class_index: int | None
    position: int
