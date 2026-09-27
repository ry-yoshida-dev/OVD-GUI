import hashlib
import string
from dataclasses import dataclass
from typing import ClassVar

from PIL import Image


@dataclass(frozen=True)
class ReferenceImage:
    """
    Identity of the pixels a reference box is drawn on, independent of where the image file lives.

    Two reference images are the same when they show the same pixels under the same name, so adding boxes on the same
    picture twice extends one visual query, and a saved class set restores its images without the original files.

    Attributes
    ----------
    name : str
        Display name, typically the file name the image was imported from; also the label of its visual query.
    digest : str
        Lowercase hexadecimal SHA-256 of the image mode, size and pixels.

    Raises
    ------
    ValueError
        If the name is blank or the digest is not a SHA-256 hex digest.
    """

    DIGEST_LENGTH: ClassVar[int] = 64

    name: str
    digest: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Reference image name must not be blank.")
        if len(self.digest) != self.DIGEST_LENGTH or any(
            character not in string.hexdigits.lower() for character in self.digest
        ):
            raise ValueError(f"digest must be a lowercase SHA-256 hex digest. got {self.digest!r}")

    @classmethod
    def of(cls, name: str, image: Image.Image) -> "ReferenceImage":
        """
        Identify an image by its pixels.

        Parameters
        ----------
        name : str
            Display name of the image.
        image : Image.Image
            Pixels to identify.

        Returns
        -------
        ReferenceImage
            Identity carrying the digest of ``image``.
        """
        return cls(name=name, digest=cls.digest_of(image))

    @staticmethod
    def digest_of(image: Image.Image) -> str:
        """
        SHA-256 of an image's mode, size and pixels.

        Parameters
        ----------
        image : Image.Image
            Pixels to hash.

        Returns
        -------
        str
            Lowercase hexadecimal digest.
        """
        width, height = image.size
        header: bytes = f"{image.mode}:{width}x{height}:".encode()
        return hashlib.sha256(header + image.tobytes()).hexdigest()
