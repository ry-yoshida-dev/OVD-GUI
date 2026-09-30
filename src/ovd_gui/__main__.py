import importlib.util
import sys

from .cli import CommandLine, InterfaceKind, LaunchOptions


def main() -> None:
    """
    Start the web interface, or the desktop window with ``--qt``; image files or directories given as arguments are
    opened at start, otherwise the images open at the end of the last session.
    """
    options: LaunchOptions = CommandLine().parse(sys.argv[1:])
    match options.interface:
        case InterfaceKind.WEB:
            from .web import WebLauncher

            WebLauncher(options.host, options.port, options.is_browser_opened).run(options.paths)
        case InterfaceKind.QT:
            if importlib.util.find_spec("PySide6") is None:
                sys.exit('The desktop window needs PySide6: pip install "ovd-gui[qt]"')
            from .gui import QtLauncher

            sys.exit(QtLauncher().run(options.paths))


if __name__ == "__main__":
    main()
