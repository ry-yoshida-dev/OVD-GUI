import io
import os
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import ClassVar

from PIL import Image

from ..media import LoadedImage
from .image_info import ImageInfo
from .image_preview import ImagePreview


class ImagePreviewCache:
    """
    Upright images encoded for the browser, which cannot display every format the detector reads, such as TIFF.

    Images are encoded as JPEG, downscaled when larger than ``MAX_SIDE``, and the latest ones are kept in memory.
    Boxes stay in the pixels of the full upright image; the browser scales them with the size of ``info_of``. Safe to
    use from several threads.
    """

    MAX_SIDE: ClassVar[int] = 4096
    CAPACITY: ClassVar[int] = 24
    JPEG_QUALITY: ClassVar[int] = 90
    TRANSPOSING_ORIENTATIONS: ClassVar[frozenset[int]] = frozenset({5, 6, 7, 8})
    ORIENTATION_TAG: ClassVar[int] = 0x0112

    def __init__(self) -> None:
        self._lock: Lock = Lock()
        self._previews: OrderedDict[tuple[Path, str], ImagePreview] = OrderedDict()
        self._infos: dict[Path, ImageInfo] = {}

    @staticmethod
    def version_of(path: Path) -> str:
        """
        Version of an image file.

        Parameters
        ----------
        path : Path
            Image file.

        Returns
        -------
        str
            Modification time in nanoseconds and size in bytes.

        Raises
        ------
        OSError
            If the file cannot be inspected.
        """
        stat: os.stat_result = path.stat()
        return f"{stat.st_mtime_ns}-{stat.st_size}"

    def info_of(self, path: Path) -> ImageInfo:
        """
        Version and upright size of an image file.

        Parameters
        ----------
        path : Path
            Image file.

        Returns
        -------
        ImageInfo
            Info read from the file header, remembered until the file changes.

        Raises
        ------
        OSError
            If the file cannot be read as an image.
        """
        version: str = self.version_of(path)
        with self._lock:
            cached: ImageInfo | None = self._infos.get(path)
        if cached is not None and cached.version == version:
            return cached
        with Image.open(path) as image:
            width, height = image.size
            orientation: object = image.getexif().get(self.ORIENTATION_TAG)
        if isinstance(orientation, int) and orientation in self.TRANSPOSING_ORIENTATIONS:
            width, height = height, width
        info: ImageInfo = ImageInfo(version=version, width=width, height=height)
        with self._lock:
            self._infos[path] = info
        return info

    def preview_of(self, path: Path) -> ImagePreview:
        """
        Encoded upright image.

        Parameters
        ----------
        path : Path
            Image file.

        Returns
        -------
        ImagePreview
            JPEG of the image, at most ``MAX_SIDE`` pixels on its longer side.

        Raises
        ------
        OSError
            If the file cannot be read as an image.
        """
        key: tuple[Path, str] = (path, self.version_of(path))
        with self._lock:
            cached: ImagePreview | None = self._previews.get(key)
            if cached is not None:
                self._previews.move_to_end(key)
                return cached
        preview: ImagePreview = self.encode(LoadedImage.open(path).image)
        with self._lock:
            self._previews[key] = preview
            while len(self._previews) > self.CAPACITY:
                self._previews.popitem(last=False)
        return preview

    @classmethod
    def encode(cls, image: Image.Image, max_side: int | None = None) -> ImagePreview:
        """
        Encode pixels as JPEG.

        Parameters
        ----------
        image : Image.Image
            RGB pixels.
        max_side : int | None, optional
            Longest side of the encoded image; ``MAX_SIDE`` by default.

        Returns
        -------
        ImagePreview
            JPEG of the image, downscaled when larger than ``max_side``.
        """
        limit: int = cls.MAX_SIDE if max_side is None else max_side
        encoded: Image.Image = image.convert("RGB")
        if max(encoded.size) > limit:
            encoded = encoded.copy()
            encoded.thumbnail((limit, limit))
        buffer: io.BytesIO = io.BytesIO()
        encoded.save(buffer, format="JPEG", quality=cls.JPEG_QUALITY)
        return ImagePreview(content=buffer.getvalue(), media_type="image/jpeg")
