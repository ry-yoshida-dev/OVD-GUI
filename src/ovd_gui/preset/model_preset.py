from dataclasses import dataclass
from importlib.resources.abc import Traversable

from dataclass_initializer import DataclassInitializer
from omegaconf import DictConfig, ListConfig, OmegaConf
from open_vocabulary_detector import DetectorBackend, DetectorSettings


@dataclass(frozen=True)
class ModelPreset:
    """
    YAML preset of one model, whose ``detector`` section maps onto ``DetectorSettings``.

    Attributes
    ----------
    backend : DetectorBackend
        Detector family the preset belongs to.
    name : str
        Preset name, e.g. ``"tiny"`` or ``"26s"``.
    source : Traversable
        YAML file holding the preset.
    """

    SECTION_KEY = "detector"

    backend: DetectorBackend
    name: str
    source: Traversable

    @property
    def label(self) -> str:
        """
        Human-readable name of the preset.

        Returns
        -------
        str
            ``"<backend>/<name>"``.
        """
        return f"{self.backend.value}/{self.name}"

    def load_settings(self) -> DetectorSettings:
        """
        Parse the preset into detector settings.

        Returns
        -------
        DetectorSettings
            Settings described by the ``detector`` section.

        Raises
        ------
        KeyError
            If the file has no ``detector`` section.
        TypeError
            If the ``detector`` section is not a mapping.
        ValueError
            If the section is for another backend or does not describe valid settings.
        """
        config: DictConfig | ListConfig = OmegaConf.create(self.source.read_text(encoding="utf-8"))
        if not isinstance(config, DictConfig) or self.SECTION_KEY not in config:
            raise KeyError(f"{self.label}: missing '{self.SECTION_KEY}' section")
        section: object = config[self.SECTION_KEY]
        if not isinstance(section, DictConfig):
            raise TypeError(f"{self.label}: '{self.SECTION_KEY}' must be a mapping")
        settings: DetectorSettings = DataclassInitializer.build(DetectorSettings, section)
        if settings.backend is not self.backend:
            raise ValueError(f"{self.label}: preset declares backend {settings.backend}")
        return settings
