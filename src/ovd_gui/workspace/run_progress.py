from dataclasses import dataclass


@dataclass(frozen=True)
class RunProgress:
    """
    Progress of the batch in progress.

    Attributes
    ----------
    title : str
        Name of the running task, e.g. ``"Detect All"``.
    processed_count : int
        Images processed so far.
    total_count : int
        Images in the batch.
    is_blocking : bool
        Whether the user should wait for the batch, as for an export.
    """

    title: str
    processed_count: int
    total_count: int
    is_blocking: bool
