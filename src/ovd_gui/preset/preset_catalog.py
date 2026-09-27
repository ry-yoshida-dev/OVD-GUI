from importlib.resources import files
from importlib.resources.abc import Traversable

from open_vocabulary_detector import DetectorBackend

from .model_preset import ModelPreset


class PresetCatalog:
    """
    Model presets grouped by backend, discovered from ``<root>/<backend>/<name>.yaml``.

    Attributes
    ----------
    presets : tuple[ModelPreset, ...]
        Every discovered preset, ordered by backend then name.
    """

    PACKAGE_NAME = "open_vocabulary_detector"
    CONFIG_DIRECTORY_NAME = "config"
    PRESET_SUFFIX = ".yaml"

    def __init__(self, root: Traversable) -> None:
        """
        Parameters
        ----------
        root : Traversable
            Directory with one sub-directory of YAML presets per backend.

        Raises
        ------
        FileNotFoundError
            If ``root`` is not a directory or holds no preset.
        """
        if not root.is_dir():
            raise FileNotFoundError(f"preset directory not found: {root}")
        self.presets: tuple[ModelPreset, ...] = tuple(
            preset for backend in DetectorBackend for preset in self._discover(root, backend)
        )
        if not self.presets:
            raise FileNotFoundError(f"no presets found under {root}")

    @classmethod
    def from_package(cls) -> "PresetCatalog":
        """
        Build the catalog of presets shipped with ``open_vocabulary_detector``.

        Returns
        -------
        PresetCatalog
            Catalog of the bundled presets.
        """
        return cls(files(cls.PACKAGE_NAME).joinpath(cls.CONFIG_DIRECTORY_NAME))

    @property
    def backends(self) -> tuple[DetectorBackend, ...]:
        """
        Backends having at least one preset.

        Returns
        -------
        tuple[DetectorBackend, ...]
            Backends in declaration order.
        """
        return tuple(backend for backend in DetectorBackend if self.presets_of(backend))

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
            Presets ordered by name.
        """
        return tuple(preset for preset in self.presets if preset.backend is backend)

    def _discover(self, root: Traversable, backend: DetectorBackend) -> list[ModelPreset]:
        backend_directory: Traversable = root.joinpath(backend.value)
        if not backend_directory.is_dir():
            return []
        preset_files: list[Traversable] = [
            entry
            for entry in backend_directory.iterdir()
            if entry.is_file() and entry.name.endswith(self.PRESET_SUFFIX)
        ]
        return [
            ModelPreset(backend=backend, name=entry.name.removesuffix(self.PRESET_SUFFIX), source=entry)
            for entry in sorted(preset_files, key=lambda entry: entry.name)
        ]
