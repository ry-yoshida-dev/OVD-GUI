from enum import Enum


class ActionStatus(Enum):
    """
    How the workspace answered a request of the user.
    """

    DONE = "done"
    REJECTED = "rejected"
    NEEDS_APPROVAL = "needs_approval"
