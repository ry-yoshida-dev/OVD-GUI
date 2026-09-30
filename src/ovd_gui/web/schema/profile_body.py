from pydantic import BaseModel


class ProfileBody(BaseModel):
    """
    Stored detector profile, or none.

    Attributes
    ----------
    key : str | None
        Key of the profile as sent in the state; ``None`` for none.
    """

    key: str | None
