from pydantic import BaseModel


class PathsBody(BaseModel):
    """
    Files or directories on the server.

    Attributes
    ----------
    paths : list[str]
        Absolute paths, or paths relative to the working directory of the server.
    """

    paths: list[str]
