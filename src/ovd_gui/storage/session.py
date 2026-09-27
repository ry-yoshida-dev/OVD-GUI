from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Session:
    """
    Images open in the window, restored at the next start.

    Attributes
    ----------
    image_paths : tuple[Path, ...]
        Open image files in list order.
    current_path : Path | None
        Image shown in the window; ``None`` when no image is shown.

    Raises
    ------
    ValueError
        If ``current_path`` is not one of ``image_paths``.
    """

    image_paths: tuple[Path, ...] = ()
    current_path: Path | None = None

    def __post_init__(self) -> None:
        if self.current_path is not None and self.current_path not in self.image_paths:
            raise ValueError(f"current_path must be one of image_paths. got {self.current_path}")
