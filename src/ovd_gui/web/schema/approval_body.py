from pydantic import BaseModel


class ApprovalBody(BaseModel):
    """
    Request of a detection run.

    Attributes
    ----------
    is_skipping_approved : bool
        Whether the user approved leaving out classes the model cannot query.
    """

    is_skipping_approved: bool = False
