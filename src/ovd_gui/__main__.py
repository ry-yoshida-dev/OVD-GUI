import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .detection import DeviceAvailability
from .gui import MainWindow
from .preset import PresetCatalog
from .storage import ClassSetStore, ClassThresholdStore, ResultStore, SessionStore
from .vocabulary import ClassListStore


def main() -> None:
    """
    Launch the GUI; image files or directories given as arguments are opened at start, otherwise the images open
    when the window last closed.
    """
    application: QApplication = QApplication(sys.argv)
    window: MainWindow = MainWindow(
        PresetCatalog.from_package(),
        ClassListStore.in_working_directory(),
        ClassSetStore.in_working_directory(),
        DeviceAvailability.detect(),
        ResultStore.in_working_directory(),
        ClassThresholdStore.in_working_directory(),
        SessionStore.in_working_directory(),
    )
    window.show()
    argument_paths: list[Path] = [Path(argument) for argument in sys.argv[1:]]
    if argument_paths:
        window.open_paths(argument_paths)
    else:
        window.restore_session()
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
