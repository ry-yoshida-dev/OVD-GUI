import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .gui import MainWindow
from .preset import PresetCatalog
from .vocabulary import ClassListStore


def main() -> None:
    """
    Launch the GUI; image files or directories given as arguments are opened at start.
    """
    application: QApplication = QApplication(sys.argv)
    window: MainWindow = MainWindow(PresetCatalog.from_package(), ClassListStore.in_working_directory())
    window.show()
    window.open_paths([Path(argument) for argument in sys.argv[1:]])
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
