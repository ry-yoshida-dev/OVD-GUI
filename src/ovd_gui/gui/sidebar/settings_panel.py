from dataclasses import replace

from open_vocabulary_detector import DetectionThresholds, DetectorBackend, DetectorSettings, Device
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QWidget,
)

from ...preset import ModelPreset, PresetCatalog


class SettingsPanel(QWidget):
    """
    Model selection from presets, with per-run overrides of device, precision and thresholds.

    Choosing a preset loads its ``DetectorSettings`` and fills every override with the preset values;
    ``current_settings`` returns the preset settings with the overrides applied.

    Signals
    -------
    backend_changed : Signal()
        Another backend was selected.
    """

    backend_changed: Signal = Signal()

    THRESHOLD_STEP = 0.05
    THRESHOLD_DECIMALS = 3

    def __init__(self, catalog: PresetCatalog, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        catalog : PresetCatalog
            Presets to choose from.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._catalog: PresetCatalog = catalog
        self._backends: tuple[DetectorBackend, ...] = catalog.backends
        self._presets: tuple[ModelPreset, ...] = ()
        self._preset_settings: DetectorSettings | None = None

        self._backend_combo: QComboBox = QComboBox()
        self._backend_combo.addItems([backend.value for backend in self._backends])
        self._preset_combo: QComboBox = QComboBox()
        self._devices: tuple[Device, ...] = tuple(Device)
        self._device_combo: QComboBox = QComboBox()
        self._device_combo.addItems([device.value for device in self._devices])
        self._half_precision_check: QCheckBox = QCheckBox("float16 (GPU only)")
        self._confidence_spin: QDoubleSpinBox = self._threshold_spin()
        self._nms_check: QCheckBox = QCheckBox("NMS IoU")
        self._nms_spin: QDoubleSpinBox = self._threshold_spin()
        self._nms_check.toggled.connect(self._nms_spin.setEnabled)

        nms_row: QWidget = QWidget()
        nms_layout: QHBoxLayout = QHBoxLayout(nms_row)
        nms_layout.setContentsMargins(0, 0, 0, 0)
        nms_layout.addWidget(self._nms_check)
        nms_layout.addWidget(self._nms_spin, stretch=1)

        layout: QFormLayout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addRow("Backend", self._backend_combo)
        layout.addRow("Preset", self._preset_combo)
        layout.addRow("Device", self._device_combo)
        layout.addRow("Precision", self._half_precision_check)
        layout.addRow("Confidence", self._confidence_spin)
        layout.addRow("NMS", nms_row)

        self._backend_combo.currentIndexChanged.connect(self._on_backend_changed)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self._on_backend_changed(self._backend_combo.currentIndex())

    @property
    def selected_backend(self) -> DetectorBackend:
        """
        Backend chosen in the panel.

        Returns
        -------
        DetectorBackend
            Selected detector family.
        """
        return self._backends[self._backend_combo.currentIndex()]

    def select_preset(self, backend: DetectorBackend, preset_name: str) -> None:
        """
        Choose a preset programmatically.

        Parameters
        ----------
        backend : DetectorBackend
            Detector family of the preset.
        preset_name : str
            Preset name within the backend.

        Raises
        ------
        KeyError
            If no such preset exists.
        """
        if backend not in self._backends:
            raise KeyError(f"no presets for backend {backend}")
        self._backend_combo.setCurrentIndex(self._backends.index(backend))
        preset_names: list[str] = [preset.name for preset in self._presets]
        if preset_name not in preset_names:
            raise KeyError(f"no preset {preset_name} for backend {backend}. available: {preset_names}")
        self._preset_combo.setCurrentIndex(preset_names.index(preset_name))

    def current_settings(self) -> DetectorSettings:
        """
        Settings of the chosen preset with the overrides of the panel applied.

        Returns
        -------
        DetectorSettings
            Settings to detect with.

        Raises
        ------
        RuntimeError
            If no preset is loaded.
        ValueError
            If an override is invalid.
        """
        if self._preset_settings is None:
            raise RuntimeError("no preset is loaded")
        return replace(
            self._preset_settings,
            device=self._devices[self._device_combo.currentIndex()],
            is_half_precision_enabled=self._half_precision_check.isChecked(),
            thresholds=DetectionThresholds(
                confidence_threshold=self._confidence_spin.value(),
                nms_iou_threshold=self._nms_spin.value() if self._nms_check.isChecked() else None,
            ),
        )

    def _threshold_spin(self) -> QDoubleSpinBox:
        spin: QDoubleSpinBox = QDoubleSpinBox()
        spin.setRange(0.0, 1.0)
        spin.setSingleStep(self.THRESHOLD_STEP)
        spin.setDecimals(self.THRESHOLD_DECIMALS)
        return spin

    def _on_backend_changed(self, index: int) -> None:
        self._presets = self._catalog.presets_of(self._backends[index])
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        self._preset_combo.addItems([preset.name for preset in self._presets])
        self._preset_combo.blockSignals(False)
        self._on_preset_changed(self._preset_combo.currentIndex())
        self.backend_changed.emit()

    def _on_preset_changed(self, index: int) -> None:
        settings: DetectorSettings = self._presets[index].load_settings()
        self._preset_settings = settings
        self._device_combo.setCurrentIndex(self._devices.index(settings.device))
        self._half_precision_check.setChecked(settings.is_half_precision_enabled)
        self._confidence_spin.setValue(settings.thresholds.confidence_threshold)
        is_nms_enabled: bool = settings.thresholds.nms_iou_threshold is not None
        self._nms_check.setChecked(is_nms_enabled)
        self._nms_spin.setEnabled(is_nms_enabled)
        self._nms_spin.setValue(settings.thresholds.nms_iou_threshold or 0.5)
