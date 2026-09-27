from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps


@dataclass(frozen=True, eq=False)
class LoadedImage:
    """
    Image read from disk, upright according to its EXIF orientation.

    Attributes
    ----------
    path : Path
        Source file.
    image : Image.Image
        RGB pixels given to the detector.
    """

    SUPPORTED_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"})

    path: Path
    image: Image.Image

    @classmethod
    def open(cls, path: Path) -> "LoadedImage":
        """
        Read an image file.

        Parameters
        ----------
        path : Path
            Image file.

        Returns
        -------
        LoadedImage
            Upright RGB image.
        """
        with Image.open(path) as source:
            upright: Image.Image = ImageOps.exif_transpose(source)
            rgb_image: Image.Image = upright.convert("RGB")
        return cls(path=path, image=rgb_image)

    @classmethod
    def is_supported(cls, path: Path) -> bool:
        """
        Whether ``path`` looks like a readable image file.

        Parameters
        ----------
        path : Path
            Candidate file.

        Returns
        -------
        bool
            True for a file with a supported suffix.
        """
        return path.is_file() and path.suffix.lower() in cls.SUPPORTED_SUFFIXES

    @classmethod
    def suffix_patterns(cls) -> str:
        """
        Glob patterns of the supported files, for file dialog filters.

        Returns
        -------
        str
            Space-separated patterns, e.g. ``"*.bmp *.jpeg *.jpg"``.
        """
        return " ".join(f"*{suffix}" for suffix in sorted(cls.SUPPORTED_SUFFIXES))

    @classmethod
    def supported_format_label(cls) -> str:
        """
        Human-readable list of the supported file formats.

        Returns
        -------
        str
            Upper-case suffixes without dots, e.g. ``"BMP · JPEG · JPG"``.
        """
        return " · ".join(sorted(suffix.removeprefix(".").upper() for suffix in cls.SUPPORTED_SUFFIXES))
