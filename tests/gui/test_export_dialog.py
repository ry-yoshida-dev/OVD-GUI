import pytest
from object_detection_format import AnnotationFormat
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialogButtonBox, QLineEdit, QPushButton

from ovd_gui.gui.export_dialog import ExportDialog


@pytest.fixture
def dialog(application: QApplication) -> ExportDialog:
    return ExportDialog()


def _child[WidgetType: QComboBox | QCheckBox | QLineEdit | QDialogButtonBox](
    dialog: ExportDialog, widget_type: type[WidgetType]
) -> WidgetType:
    widget: WidgetType | None = dialog.findChild(widget_type)
    assert widget is not None
    return widget


def test_confidence_is_enabled_only_for_formats_that_store_it(dialog: ExportDialog) -> None:
    format_combo: QComboBox = _child(dialog, QComboBox)
    confidence_check: QCheckBox = _child(dialog, QCheckBox)
    for index, annotation_format in enumerate(AnnotationFormat):
        format_combo.setCurrentIndex(index)
        assert dialog.selected_format is annotation_format
        assert confidence_check.isEnabled() is (annotation_format in {AnnotationFormat.COCO, AnnotationFormat.YOLO})


def test_save_requires_an_output_directory(dialog: ExportDialog) -> None:
    save_button: QPushButton = _child(dialog, QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save)
    assert not save_button.isEnabled()
    _child(dialog, QLineEdit).setText("  ")
    assert not save_button.isEnabled()
    _child(dialog, QLineEdit).setText("/tmp/export")
    assert save_button.isEnabled()
