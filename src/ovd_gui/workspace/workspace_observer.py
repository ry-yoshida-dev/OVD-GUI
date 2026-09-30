from typing import Protocol

from .notice import Notice
from .workspace_topic import WorkspaceTopic


class WorkspaceObserver(Protocol):
    """
    View following the workspace, always called on the thread owning the workspace.
    """

    def on_changed(self, topics: frozenset[WorkspaceTopic]) -> None:
        """
        Parts of the workspace changed and should be shown again.

        Parameters
        ----------
        topics : frozenset[WorkspaceTopic]
            Changed parts.
        """
        ...

    def on_notice(self, notice: Notice) -> None:
        """
        Something happened that the user should be told about.

        Parameters
        ----------
        notice : Notice
            Message for the user.
        """
        ...
