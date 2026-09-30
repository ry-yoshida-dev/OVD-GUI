from dataclasses import dataclass
from pathlib import Path

from .interface_kind import InterfaceKind


@dataclass(frozen=True)
class LaunchOptions:
    """
    What the command line asks to start.

    Attributes
    ----------
    interface : InterfaceKind
        Web server or desktop window.
    paths : tuple[Path, ...]
        Images or directories opened at start; empty to open the images of the last session.
    host : str
        Interface the web server listens on.
    port : int
        Port the web server listens on.
    is_browser_opened : bool
        Whether the web interface is opened in the default browser.
    """

    interface: InterfaceKind
    paths: tuple[Path, ...]
    host: str
    port: int
    is_browser_opened: bool
