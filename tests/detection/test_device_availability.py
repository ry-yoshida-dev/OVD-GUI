import pytest
from open_vocabulary_detector import Device

from ovd_gui.detection import DeviceAvailability


@pytest.mark.parametrize(
    ("availability", "supported_devices"),
    [
        (DeviceAvailability(is_cuda_available=False, is_mps_available=False), set[Device]()),
        (DeviceAvailability(is_cuda_available=True, is_mps_available=False), {Device.AUTO, Device.CUDA}),
        (DeviceAvailability(is_cuda_available=False, is_mps_available=True), {Device.AUTO, Device.MPS}),
    ],
)
def test_half_precision_is_supported_only_on_available_gpus(
    availability: DeviceAvailability, supported_devices: set[Device]
) -> None:
    assert {device for device in Device if availability.is_half_precision_supported(device)} == supported_devices


def test_missing_gpu_backends_are_unavailable() -> None:
    availability: DeviceAvailability = DeviceAvailability(is_cuda_available=False, is_mps_available=True)
    assert {device for device in Device if availability.is_available(device)} == {Device.AUTO, Device.CPU, Device.MPS}
