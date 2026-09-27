from pathlib import Path

from object_detection_format import AnnotationFormat
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..export import ExportOptions


class ExportDialog(QDialog):
    """
    Choice of annotation format, output directory and confidence setting for detecting every open image and
    exporting the results.

    The dialog keeps its values between openings, so it is meant to be created once and reused.
    """

    WINDOW_TITLE = "Export Detections"

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumWidth(460)

        self._formats: tuple[AnnotationFormat, ...] = tuple(AnnotationFormat)
        self._format_combo: QComboBox = QComboBox()
        self._format_combo.addItems([annotation_format.display_name for annotation_format in self._formats])
        self._directory_edit: QLineEdit = QLineEdit()
        self._directory_edit.setPlaceholderText("Directory receiving the annotation files")
        self._browse_button: QPushButton = QPushButton("Browse…")
        self._confidence_check: QCheckBox = QCheckBox("Include confidence")
        self._confidence_check.setChecked(True)
        self._summary_label: QLabel = QLabel()
        self._summary_label.setWordWrap(True)
        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )

        directory_row: QWidget = QWidget()
        directory_layout: QHBoxLayout = QHBoxLayout(directory_row)
        directory_layout.setContentsMargins(0, 0, 0, 0)
        directory_layout.addWidget(self._directory_edit, stretch=1)
        directory_layout.addWidget(self._browse_button)

        form_layout: QFormLayout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form_layout.addRow("Format", self._format_combo)
        form_layout.addRow("Output", directory_row)
        form_layout.addRow("", self._confidence_check)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.addWidget(self._summary_label)
        layout.addLayout(form_layout)
        layout.addWidget(self._button_box)

        self._format_combo.currentIndexChanged.connect(self._update_confidence_support)
        self._directory_edit.textChanged.connect(self._update_save_button)
        self._browse_button.clicked.connect(self._choose_directory)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        self._update_confidence_support()
        self._update_save_button()

    @property
    def selected_format(self) -> AnnotationFormat:
        """
        Format chosen in the dialog.

        Returns
        -------
        AnnotationFormat
            Selected output format.
        """
        return self._formats[self._format_combo.currentIndex()]

    def ask(self, image_count: int) -> ExportOptions | None:
        """
        Show the dialog modally.

        Parameters
        ----------
        image_count : int
            Number of images that will be detected and exported, shown to the user.

        Returns
        -------
        ExportOptions | None
            Chosen options, or None if the dialog was cancelled.
        """
        self._summary_label.setText(
            f"Detect all {image_count} image{'' if image_count == 1 else 's'} with the current model and classes, "
            + "then save the results."
        )
        if self.exec() != QDialog.DialogCode.Accepted:
            return None
        return ExportOptions(
            annotation_format=self.selected_format,
            output_directory=Path(self._directory_edit.text().strip()).expanduser(),
            is_confidence_included=self._confidence_check.isEnabled() and self._confidence_check.isChecked(),
        )

    def _choose_directory(self) -> None:
        directory: str = QFileDialog.getExistingDirectory(self, "Export To", self._directory_edit.text())
        if directory:
            self._directory_edit.setText(directory)

    def _update_confidence_support(self) -> None:
        is_supported: bool = ExportOptions.is_confidence_supported(self.selected_format)
        self._confidence_check.setEnabled(is_supported)
        self._confidence_check.setToolTip(
            "Write each detection's confidence" if is_supported else "This format has no confidence field"
        )

    def _update_save_button(self) -> None:
        save_button: QPushButton = self._button_box.button(QDialogButtonBox.StandardButton.Save)
        save_button.setEnabled(bool(self._directory_edit.text().strip()))
