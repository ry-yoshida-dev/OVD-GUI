from dataclasses import dataclass
from pathlib import Path

from open_vocabulary_detector import DetectorSettings
from PIL import Image

from .labeled_prompt import LabeledPrompt


@dataclass(frozen=True, eq=False)
class DetectionRequest:
    """
    Detection in one open image.

    Attributes
    ----------
    settings : DetectorSettings
        Model and thresholds to detect with.
    image_path : Path
        File the image was read from, identifying whose result the outcome is.
    image : Image.Image
        RGB image to detect in.
    labeled_prompt : LabeledPrompt
        Classes to detect with their queries, and the label of each query.
    """

    settings: DetectorSettings
    image_path: Path
    image: Image.Image
    labeled_prompt: LabeledPrompt
