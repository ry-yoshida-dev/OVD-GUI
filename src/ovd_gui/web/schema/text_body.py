from pydantic import BaseModel


class TextBody(BaseModel):
    """
    Text typed by the user.

    Attributes
    ----------
    text : str
        Text, e.g. one class per line.
    """

    text: str
