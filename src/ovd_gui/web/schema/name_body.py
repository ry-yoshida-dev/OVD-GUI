from pydantic import BaseModel


class NameBody(BaseModel):
    """
    Name typed by the user.

    Attributes
    ----------
    name : str
        New name.
    """

    name: str
