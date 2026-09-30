import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from .interface_kind import InterfaceKind
from .launch_options import LaunchOptions


class CommandLine:
    """
    Arguments of the ``ovd-gui`` command.

    The web interface starts by default; ``--qt`` starts the desktop window instead, which needs the ``qt`` extra.
    """

    DEFAULT_HOST: ClassVar[str] = "127.0.0.1"
    DEFAULT_PORT: ClassVar[int] = 8000

    def __init__(self) -> None:
        self._parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog="ovd-gui",
            description="Open-vocabulary object detection GUI. Starts a web server by default.",
        )
        self._parser.add_argument(
            "paths", nargs="*", type=Path, help="images or folders to open; the last session is restored without any"
        )
        self._parser.add_argument(
            "--qt", action="store_true", help="start the PySide6 desktop window instead of the web interface"
        )
        self._parser.add_argument(
            "--host",
            default=self.DEFAULT_HOST,
            help=f"interface the web server listens on (default {self.DEFAULT_HOST}; 0.0.0.0 exposes it to the network)",
        )
        self._parser.add_argument(
            "--port", type=int, default=self.DEFAULT_PORT, help=f"port of the web server (default {self.DEFAULT_PORT})"
        )
        self._parser.add_argument(
            "--no-browser", action="store_true", help="do not open the web interface in the default browser"
        )

    def parse(self, arguments: Sequence[str]) -> LaunchOptions:
        """
        Read the command-line arguments.

        Parameters
        ----------
        arguments : Sequence[str]
            Arguments without the program name.

        Returns
        -------
        LaunchOptions
            What to start.
        """
        namespace: argparse.Namespace = self._parser.parse_args(list(arguments))
        paths: list[Path] = namespace.paths
        is_qt: bool = namespace.qt
        host: str = namespace.host
        port: int = namespace.port
        is_browser_disabled: bool = namespace.no_browser
        return LaunchOptions(
            interface=InterfaceKind.QT if is_qt else InterfaceKind.WEB,
            paths=tuple(paths),
            host=host,
            port=port,
            is_browser_opened=not is_browser_disabled,
        )
