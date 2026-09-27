from dataclasses import dataclass

from open_vocabulary_detector import DetectorSettings
from PIL import Image

from .labeled_prompt import LabeledPrompt


@dataclass(frozen=True, eq=False)
class DetectionRequest:
    """
    One detection run requested by the user.

    Attributes
    ----------
    settings : DetectorSettings
        Model and thresholds to detect with.
    image : Image.Image
        RGB image to detect in.
    labeled_prompt : LabeledPrompt
        Classes to detect with their queries, and the label of each query.
    """

    settings: DetectorSettings
    image: Image.Image
    labeled_prompt: LabeledPrompt
