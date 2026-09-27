from open_vocabulary_detector import Device
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QApplication

from ovd_gui.detection import DeviceAvailability
from ovd_gui.gui.sidebar import SettingsPanel
from ovd_gui.preset import PresetCatalog


def test_half_precision_is_disabled_without_gpu(application: QApplication) -> None:
    panel: SettingsPanel = SettingsPanel(
        PresetCatalog.from_package(), DeviceAvailability(is_cuda_available=False, is_mps_available=False)
    )
    assert not panel._half_precision_check.isEnabled()
    assert not panel.current_settings().is_half_precision_enabled


def test_half_precision_follows_selected_device(application: QApplication) -> None:
    panel: SettingsPanel = SettingsPanel(
        PresetCatalog.from_package(), DeviceAvailability(is_cuda_available=False, is_mps_available=True)
    )
    panel._device_combo.setCurrentIndex(panel._devices.index(Device.MPS))
    assert panel._half_precision_check.isEnabled()
    panel._half_precision_check.setChecked(True)
    assert panel.current_settings().is_half_precision_enabled
    panel._device_combo.setCurrentIndex(panel._devices.index(Device.CPU))
    assert not panel._half_precision_check.isEnabled()
    assert not panel.current_settings().is_half_precision_enabled
    panel._device_combo.setCurrentIndex(panel._devices.index(Device.CUDA))
    assert not panel._half_precision_check.isEnabled()


def test_missing_devices_are_listed_disabled(application: QApplication) -> None:
    panel: SettingsPanel = SettingsPanel(
        PresetCatalog.from_package(), DeviceAvailability(is_cuda_available=False, is_mps_available=True)
    )
    model: object = panel._device_combo.model()
    assert isinstance(model, QStandardItemModel)
    enabled_devices: set[Device] = {device for row, device in enumerate(panel._devices) if model.item(row).isEnabled()}
    assert enabled_devices == {Device.AUTO, Device.CPU, Device.MPS}
