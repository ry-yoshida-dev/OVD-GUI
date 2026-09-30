from dataclasses import replace

from open_vocabulary_detector import DetectionThresholds, DetectorBackend, DetectorSettings, Device

from ..detection import DeviceAvailability
from ..preset import ModelPreset, PresetCatalog
from .model_selection import ModelSelection


class ModelSelector:
    """
    Presets that can be chosen, and the detector settings of a chosen preset with its overrides applied.

    Choosing a preset fills every override with the preset values. A device missing on this machine falls back to
    ``Device.AUTO``, and float16 is turned off unless the device resolves to an available GPU. Preset files are read
    once and remembered.
    """

    def __init__(self, catalog: PresetCatalog, device_availability: DeviceAvailability) -> None:
        """
        Parameters
        ----------
        catalog : PresetCatalog
            Presets to choose from; at least one.
        device_availability : DeviceAvailability
            GPU backends of this machine.

        Raises
        ------
        ValueError
            If the catalog holds no preset.
        """
        if not catalog.backends:
            raise ValueError("The preset catalog holds no preset.")
        self._catalog: PresetCatalog = catalog
        self._device_availability: DeviceAvailability = device_availability
        self._preset_settings: dict[tuple[DetectorBackend, str], DetectorSettings] = {}

    @property
    def backends(self) -> tuple[DetectorBackend, ...]:
        """
        Backends having at least one preset.

        Returns
        -------
        tuple[DetectorBackend, ...]
            Backends in catalog order.
        """
        return self._catalog.backends

    @property
    def device_availability(self) -> DeviceAvailability:
        """
        GPU backends of this machine.

        Returns
        -------
        DeviceAvailability
            Availability given at construction.
        """
        return self._device_availability

    def presets_of(self, backend: DetectorBackend) -> tuple[ModelPreset, ...]:
        """
        Presets of one backend.

        Parameters
        ----------
        backend : DetectorBackend
            Detector family.

        Returns
        -------
        tuple[ModelPreset, ...]
            Presets in catalog order.
        """
        return self._catalog.presets_of(backend)

    def default_selection(self) -> ModelSelection:
        """
        First preset of the first backend with its own values.

        Returns
        -------
        ModelSelection
            Selection of the first preset.
        """
        backend: DetectorBackend = self.backends[0]
        return self.selection_of(backend, self.presets_of(backend)[0].name)

    def selection_of(self, backend: DetectorBackend, preset_name: str) -> ModelSelection:
        """
        Selection of a preset with every override filled from the preset.

        Parameters
        ----------
        backend : DetectorBackend
            Detector family of the preset.
        preset_name : str
            Preset name within the backend.

        Returns
        -------
        ModelSelection
            Preset values, with an unavailable device replaced by ``AUTO`` and float16 turned off where it cannot
            run.

        Raises
        ------
        KeyError
            If no such preset exists.
        """
        settings: DetectorSettings = self._settings_of_preset(backend, preset_name)
        device: Device = settings.device if self._device_availability.is_available(settings.device) else Device.AUTO
        return ModelSelection(
            backend=backend,
            preset_name=preset_name,
            device=device,
            is_half_precision_enabled=settings.is_half_precision_enabled
            and self._device_availability.is_half_precision_supported(device),
            confidence_threshold=settings.thresholds.confidence_threshold,
            nms_iou_threshold=settings.thresholds.nms_iou_threshold,
        )

    def validated(self, selection: ModelSelection) -> ModelSelection:
        """
        Selection that can run on this machine.

        Parameters
        ----------
        selection : ModelSelection
            Requested selection.

        Returns
        -------
        ModelSelection
            ``selection`` with float16 turned off when its device cannot run it.

        Raises
        ------
        KeyError
            If the preset does not exist.
        ValueError
            If the device is not available on this machine.
        """
        self._settings_of_preset(selection.backend, selection.preset_name)
        if not self._device_availability.is_available(selection.device):
            raise ValueError(f"The device {selection.device.value} is not available on this machine.")
        if selection.is_half_precision_enabled and not self._device_availability.is_half_precision_supported(
            selection.device
        ):
            return replace(selection, is_half_precision_enabled=False)
        return selection

    def settings_of(self, selection: ModelSelection) -> DetectorSettings:
        """
        Settings of the chosen preset with the overrides applied.

        Parameters
        ----------
        selection : ModelSelection
            Chosen preset and overrides.

        Returns
        -------
        DetectorSettings
            Settings to detect with.

        Raises
        ------
        KeyError
            If the preset does not exist.
        """
        return replace(
            self._settings_of_preset(selection.backend, selection.preset_name),
            device=selection.device,
            is_half_precision_enabled=selection.is_half_precision_enabled,
            thresholds=DetectionThresholds(
                confidence_threshold=selection.confidence_threshold,
                nms_iou_threshold=selection.nms_iou_threshold,
            ),
        )

    def _settings_of_preset(self, backend: DetectorBackend, preset_name: str) -> DetectorSettings:
        key: tuple[DetectorBackend, str] = (backend, preset_name)
        cached: DetectorSettings | None = self._preset_settings.get(key)
        if cached is not None:
            return cached
        presets: dict[str, ModelPreset] = {preset.name: preset for preset in self._catalog.presets_of(backend)}
        if preset_name not in presets:
            raise KeyError(f"no preset {preset_name} for backend {backend.value}. available: {sorted(presets)}")
        settings: DetectorSettings = presets[preset_name].load_settings()
        self._preset_settings[key] = settings
        return settings
