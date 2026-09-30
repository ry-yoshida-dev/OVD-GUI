from dataclasses import dataclass

from .notice_level import NoticeLevel


@dataclass(frozen=True)
class Notice:
    """
    Message for the user about something that happened, such as a finished run or a failed save.

    Attributes
    ----------
    message : str
        Text shown to the user.
    level : NoticeLevel
        Whether the message is a passing status or an error to acknowledge.
    title : str
        Short heading of an error; empty for a passing status.
    """

    message: str
    level: NoticeLevel = NoticeLevel.INFO
    title: str = ""

    @classmethod
    def error(cls, title: str, message: str) -> "Notice":
        """
        Error the user should acknowledge.

        Parameters
        ----------
        title : str
            Short heading.
        message : str
            What went wrong.

        Returns
        -------
        Notice
            Notice of the ``ERROR`` level.
        """
        return cls(message=message, level=NoticeLevel.ERROR, title=title)
