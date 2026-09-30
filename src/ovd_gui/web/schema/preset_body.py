from pydantic import BaseModel


class PresetBody(BaseModel):
    """
    Preset to choose with its own values.

    Attributes
    ----------
    backend : str
        Value of the detector backend.
    preset_name : str
        Preset name within the backend.
    """

    backend: str
    preset_name: str
