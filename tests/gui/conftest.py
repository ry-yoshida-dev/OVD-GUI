import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def application() -> QApplication:
    existing: object = QApplication.instance()
    return existing if isinstance(existing, QApplication) else QApplication([])
