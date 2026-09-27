from dataclasses import dataclass

import torch
from open_vocabulary_detector import Device


@dataclass(frozen=True)
class DeviceAvailability:
    """
    GPU backends present on this machine, deciding which settings can run here.

    Attributes
    ----------
    is_cuda_available : bool
        Whether a CUDA GPU is usable.
    is_mps_available : bool
        Whether the Apple Silicon GPU is usable through Metal Performance Shaders.
    """

    is_cuda_available: bool
    is_mps_available: bool

    @classmethod
    def detect(cls) -> "DeviceAvailability":
        """
        Probe the GPU backends of this machine.

        Returns
        -------
        DeviceAvailability
            Backends PyTorch can use.
        """
        return cls(
            is_cuda_available=torch.cuda.is_available(),
            is_mps_available=torch.backends.mps.is_available(),
        )

    def is_available(self, device: Device) -> bool:
        """
        Whether a device can be requested on this machine.

        Parameters
        ----------
        device : Device
            Requested device.

        Returns
        -------
        bool
            True for ``AUTO`` and ``CPU``, and for a GPU backend present on this machine.
        """
        match device:
            case Device.AUTO | Device.CPU:
                return True
            case Device.CUDA:
                return self.is_cuda_available
            case Device.MPS:
                return self.is_mps_available

    def is_half_precision_supported(self, device: Device) -> bool:
        """
        Whether float16 can run on a device, i.e. whether it resolves to an available GPU.

        Parameters
        ----------
        device : Device
            Requested device.

        Returns
        -------
        bool
            True if the device resolves to an available GPU.
        """
        match device:
            case Device.AUTO:
                return self.is_cuda_available or self.is_mps_available
            case Device.CPU:
                return False
            case Device.CUDA | Device.MPS:
                return self.is_available(device)
