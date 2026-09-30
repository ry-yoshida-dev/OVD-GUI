from enum import Enum


class NoticeLevel(Enum):
    """
    How prominently a notice is shown to the user.
    """

    INFO = "info"
    ERROR = "error"
