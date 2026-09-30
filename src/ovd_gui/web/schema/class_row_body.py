from pydantic import BaseModel


class ClassRowBody(BaseModel):
    """
    New class, or new phrases of a class, typed by the user.

    Attributes
    ----------
    text : str
        ``name`` or ``name: phrase, phrase`` for a class; comma-separated phrases for a class id.
    class_index : int | None
        Class receiving the phrases; ``None`` to add a class.
    position : int
        Class id of the new class, or position of the first new phrase in the class.
    """

    text: str
    class_index: int | None = None
    position: int
