import webbrowser
from collections.abc import Sequence
from pathlib import Path
from threading import Timer
from typing import ClassVar

import uvicorn

from ..detection import DeviceAvailability
from ..preset import PresetCatalog
from ..workspace import ModelSelector, WorkspaceStores
from .access_guard import AccessGuard
from .web_application import WebApplication


class WebLauncher:
    """
    Starts the web server and, when asked, opens the user interface in the default browser.

    The server listens on the loopback interface by default, so only this machine can reach it; on a remote machine,
    forward the port over SSH (``ssh -L 8000:localhost:8000 host``) instead of listening on every interface. The
    printed address carries an access token created for this run; only browsers that opened it can use the server.
    """

    BROWSER_DELAY_SECONDS: ClassVar[float] = 1.0
    COOKIE_NAME_PREFIX: ClassVar[str] = "ovd_gui_token_"

    def __init__(self, host: str, port: int, is_browser_opened: bool) -> None:
        """
        Parameters
        ----------
        host : str
            Interface to listen on, e.g. ``127.0.0.1`` or ``0.0.0.0``.
        port : int
            Port to listen on.
        is_browser_opened : bool
            Whether to open the user interface in the default browser once the server runs.
        """
        self._host: str = host
        self._port: int = port
        self._is_browser_opened: bool = is_browser_opened
        self._access_token: str = AccessGuard.new_token()

    @property
    def url(self) -> str:
        """
        Address of the user interface.

        Returns
        -------
        str
            ``http://<host>:<port>/?token=<access token>``, naming ``localhost`` when listening on every interface.
        """
        shown_host: str = "localhost" if self._host in {"0.0.0.0", "::"} else self._host
        return f"http://{shown_host}:{self._port}/?{AccessGuard.TOKEN_PARAMETER}={self._access_token}"

    def run(self, initial_paths: Sequence[Path]) -> None:
        """
        Serve until interrupted.

        Parameters
        ----------
        initial_paths : Sequence[Path]
            Images or directories opened at start; without any, the images of the last session are opened again.
        """
        print("Probing devices and model presets ...", flush=True)
        application: WebApplication = WebApplication(
            ModelSelector(PresetCatalog.from_package(), DeviceAvailability.detect()),
            WorkspaceStores.in_working_directory(),
            initial_paths,
            Path.cwd(),
            self._access_token,
            f"{self.COOKIE_NAME_PREFIX}{self._port}",
        )
        print(f"OVD GUI is running at {self.url}", flush=True)
        if self._is_browser_opened:
            Timer(self.BROWSER_DELAY_SECONDS, webbrowser.open, args=(self.url,)).start()
        uvicorn.run(application.build(), host=self._host, port=self._port, log_level="warning")
