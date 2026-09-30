from pathlib import Path

from ..workspace import Workspace
from .directory_browser import DirectoryBrowser
from .event_hub import EventHub
from .image_preview_cache import ImagePreviewCache
from .payload_builder import PayloadBuilder
from .reference_draft_store import ReferenceDraftStore


class WebContext:
    """
    What the request handlers share: the workspace, created once the event loop runs, and the helpers around it.
    """

    def __init__(self, working_directory: Path) -> None:
        """
        Parameters
        ----------
        working_directory : Path
            Directory the server was started in, listed first when browsing the server.
        """
        self._workspace: Workspace | None = None
        self.working_directory: Path = working_directory
        self.hub: EventHub = EventHub()
        self.preview_cache: ImagePreviewCache = ImagePreviewCache()
        self.payloads: PayloadBuilder = PayloadBuilder(self.preview_cache)
        self.drafts: ReferenceDraftStore = ReferenceDraftStore()
        self.browser: DirectoryBrowser = DirectoryBrowser(working_directory, {})

    @property
    def workspace(self) -> Workspace:
        """
        Workspace of the running server.

        Returns
        -------
        Workspace
            Workspace attached at start.

        Raises
        ------
        RuntimeError
            If the server has not started yet.
        """
        if self._workspace is None:
            raise RuntimeError("The workspace is not ready yet.")
        return self._workspace

    def attach(self, workspace: Workspace) -> None:
        """
        Use the workspace created at start.

        Parameters
        ----------
        workspace : Workspace
            Workspace running on the event loop of the server.
        """
        self._workspace = workspace
        workspace.add_observer(self.hub)
        self.browser = DirectoryBrowser(
            self.working_directory,
            {
                "Working directory": self.working_directory,
                "Home": Path.home(),
                "Uploads": workspace.stores.upload_store.directory,
            },
        )

    def detach(self) -> None:
        """
        Stop using the workspace, e.g. when the server stops.
        """
        if self._workspace is not None:
            self._workspace.remove_observer(self.hub)
        self._workspace = None
