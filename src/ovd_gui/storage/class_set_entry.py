from dataclasses import dataclass
from datetime import datetime

from .class_set_summary import ClassSetSummary


@dataclass(frozen=True)
class ClassSetEntry:
    """
    Saved class set as listed in the data directory.

    Attributes
    ----------
    name : str
        Class set name.
    saved_at : datetime
        Time the set was last written, in the local time zone.
    summary : ClassSetSummary | None
        Counts read from the manifest, or ``None`` when the file cannot be read as a class set; such a set can
        still be renamed or deleted.
    """

    name: str
    saved_at: datetime
    summary: ClassSetSummary | None

    @property
    def is_readable(self) -> bool:
        """
        Whether the file could be read as a class set.

        Returns
        -------
        bool
            True when a summary is available.
        """
        return self.summary is not None
