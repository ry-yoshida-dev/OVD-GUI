import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ..detection import DeviceAvailability
from ..preset import PresetCatalog
from ..storage import ClassSetStore, ClassThresholdStore, ResultStore, SessionStore
from ..vocabulary import ClassListStore
from .main_window import MainWindow


class QtLauncher:
    """
    Starts the PySide6 desktop window.
    """

    def run(self, initial_paths: Sequence[Path]) -> int:
        """
        Show the main window until it is closed.

        Parameters
        ----------
        initial_paths : Sequence[Path]
            Images or directories opened at start; without any, the images open when the window last closed are
            opened again.

        Returns
        -------
        int
            Exit code of the Qt event loop.
        """
        application: QApplication = QApplication(sys.argv[:1])
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
        if initial_paths:
            window.open_paths(list(initial_paths))
        else:
            window.restore_session()
        return application.exec()
