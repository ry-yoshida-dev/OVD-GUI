from enum import Enum


class WorkspaceTopic(Enum):
    """
    Part of the workspace a view shows, reported when it changes.
    """

    STATE = "state"
    DETECTIONS = "detections"
    CLASS_SETS = "class_sets"
