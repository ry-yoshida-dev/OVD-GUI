from pydantic import BaseModel


class PathBody(BaseModel):
    """
    One file on the server.

    Attributes
    ----------
    path : str
        Absolute path, or path relative to the working directory of the server.
    """

    path: str
