from dataclasses import dataclass

from ..storage import ClassSetStore, ClassThresholdStore, ResultStore, SessionStore
from ..vocabulary import ClassListStore
from .upload_store import UploadStore


@dataclass(frozen=True)
class WorkspaceStores:
    """
    Data directories the workspace reads at start and writes after changes.

    Attributes
    ----------
    class_list_store : ClassListStore
        Class list of the last run.
    class_set_store : ClassSetStore
        Saved class sets with their reference images.
    result_store : ResultStore
        Detection results of every model.
    class_threshold_store : ClassThresholdStore
        Minimum confidence of each class.
    session_store : SessionStore
        Open images and the shown one.
    upload_store : UploadStore
        Image files sent from a browser.
    """

    class_list_store: ClassListStore
    class_set_store: ClassSetStore
    result_store: ResultStore
    class_threshold_store: ClassThresholdStore
    session_store: SessionStore
    upload_store: UploadStore

    @classmethod
    def in_working_directory(cls) -> "WorkspaceStores":
        """
        Stores in ``ovd_gui_data`` under the current working directory.

        Returns
        -------
        WorkspaceStores
            Every store of the data directory.
        """
        return cls(
            class_list_store=ClassListStore.in_working_directory(),
            class_set_store=ClassSetStore.in_working_directory(),
            result_store=ResultStore.in_working_directory(),
            class_threshold_store=ClassThresholdStore.in_working_directory(),
            session_store=SessionStore.in_working_directory(),
            upload_store=UploadStore.in_working_directory(),
        )
