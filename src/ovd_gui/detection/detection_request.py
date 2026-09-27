from dataclasses import dataclass
from pathlib import Path

from open_vocabulary_detector import DetectorSettings

from .labeled_prompt import LabeledPrompt


@dataclass(frozen=True, eq=False)
class DetectionRequest:
    """
    Detection in one image file.

    The file is read where the detection runs, so a request can be made on the GUI thread without reading pixels.

    Attributes
    ----------
    settings : DetectorSettings
        Model and thresholds to detect with.
    image_path : Path
        Image file to detect in, identifying whose result the outcome is.
    labeled_prompt : LabeledPrompt
        Classes to detect with their queries, and the label of each query.
    """

    settings: DetectorSettings
    image_path: Path
    labeled_prompt: LabeledPrompt
