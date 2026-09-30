from pydantic import BaseModel


class ThresholdsBody(BaseModel):
    """
    Minimum confidence of each class.

    Attributes
    ----------
    default_minimum : float
        Minimum of every class without its own.
    class_minimums : dict[str, float]
        Classes with their own minimum.
    """

    default_minimum: float
    class_minimums: dict[str, float]
