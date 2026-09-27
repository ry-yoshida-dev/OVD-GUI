import io
import json
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from PIL import Image

from ..detection import ReferenceBox, ReferenceImage
from ..vocabulary import ClassDefinition
from .class_set import ClassSet
from .class_set_summary import ClassSetSummary
from .json_fields import JsonFields, JsonValue


class ClassSetArchive:
    """
    Class set stored as one self-contained ZIP file.

    ``manifest.json`` lists the classes with their phrases, the reference images and the reference boxes; the pixels
    of every reference image are stored losslessly as ``images/<sha256>.png``, so the file restores its image prompts
    on any machine, wherever the original images were. Writing goes through a temporary file, so a failed write
    leaves an existing archive intact.

    ``manifest.json`` looks like::

        {
          "format": "ovd-gui-class-set",
          "version": 1,
          "classes": [{"name": "car", "phrases": ["car", "suv"]}],
          "reference_images": [{"name": "sedan.jpg", "digest": "<sha256>", "file": "images/<sha256>.png"}],
          "reference_boxes": [{"class_name": "car", "image": 0, "xyxy": [12.0, 30.0, 220.0, 140.0]}]
        }

    ``image`` is the index of the box's image in ``reference_images``.
    """

    SUFFIX: ClassVar[str] = ".ovdset"
    FORMAT_NAME: ClassVar[str] = "ovd-gui-class-set"
    FORMAT_VERSION: ClassVar[int] = 1
    MANIFEST_NAME: ClassVar[str] = "manifest.json"
    IMAGE_DIRECTORY: ClassVar[str] = "images"
    PARTIAL_SUFFIX: ClassVar[str] = ".partial"

    def __init__(self, path: Path) -> None:
        """
        Parameters
        ----------
        path : Path
            Location of the archive.
        """
        self._path: Path = path

    @property
    def path(self) -> Path:
        """
        Location of the archive.

        Returns
        -------
        Path
            Path given at construction.
        """
        return self._path

    @classmethod
    def is_archive_path(cls, path: Path) -> bool:
        """
        Whether a path names a class set archive by its suffix.

        Parameters
        ----------
        path : Path
            Candidate file.

        Returns
        -------
        bool
            True for a ``.ovdset`` file name, regardless of case.
        """
        return path.suffix.lower() == cls.SUFFIX

    def read(self) -> ClassSet:
        """
        Read the class set.

        Returns
        -------
        ClassSet
            Classes, reference boxes and the pixels of the reference images.

        Raises
        ------
        OSError
            If the file cannot be read.
        ValueError
            If the file is not a class set archive, its content is invalid, or an image does not match its digest.
        """
        return self._read_with(self._class_set_from)

    def read_summary(self) -> ClassSetSummary:
        """
        Read the counts of the class set from its manifest, without decoding any image.

        Returns
        -------
        ClassSetSummary
            Class names, phrase count and reference image count.

        Raises
        ------
        OSError
            If the file cannot be read.
        ValueError
            If the file is not a class set archive or its manifest is invalid.
        """
        return self._read_with(self._summary_from)

    def _read_with[T](self, reader: Callable[[zipfile.ZipFile, dict[str, JsonValue]], T]) -> T:
        try:
            with zipfile.ZipFile(self._path) as archive:
                manifest: dict[str, JsonValue] = JsonFields.object_of(
                    JsonFields.parse(archive.read(self.MANIFEST_NAME).decode("utf-8")), "manifest"
                )
                self._require_format(manifest)
                return reader(archive, manifest)
        except zipfile.BadZipFile as error:
            raise ValueError(f"{self._path.name} is not a class set archive: {error}") from error
        except KeyError as error:
            raise ValueError(f"{self._path.name} lacks an entry: {error}") from error
        except UnicodeDecodeError as error:
            raise ValueError(f"{self.MANIFEST_NAME} of {self._path.name} is not UTF-8 text.") from error
        except json.JSONDecodeError as error:
            raise ValueError(f"{self.MANIFEST_NAME} of {self._path.name} is not valid JSON: {error}") from error
        except TypeError as error:
            raise ValueError(f"{self.MANIFEST_NAME} of {self._path.name} is malformed: {error}") from error

    def _summary_from(self, archive: zipfile.ZipFile, manifest: dict[str, JsonValue]) -> ClassSetSummary:
        classes: tuple[ClassDefinition, ...] = tuple(
            self._class_of(JsonFields.object_of(entry, "class"))
            for entry in JsonFields.list_of(manifest.get("classes"), "classes")
        )
        return ClassSetSummary(
            class_names=tuple(definition.name for definition in classes),
            phrase_count=sum(len(definition.text_queries) for definition in classes),
            reference_image_count=len(JsonFields.list_of(manifest.get("reference_images"), "reference_images")),
        )

    def _class_set_from(self, archive: zipfile.ZipFile, manifest: dict[str, JsonValue]) -> ClassSet:
        reference_images: list[ReferenceImage] = []
        reference_pixels: dict[ReferenceImage, Image.Image] = {}
        for entry in JsonFields.list_of(manifest.get("reference_images"), "reference_images"):
            reference_image, pixels = self._read_image(archive, JsonFields.object_of(entry, "reference image"))
            reference_images.append(reference_image)
            reference_pixels[reference_image] = pixels
        return ClassSet(
            classes=tuple(
                self._class_of(JsonFields.object_of(entry, "class"))
                for entry in JsonFields.list_of(manifest.get("classes"), "classes")
            ),
            reference_boxes=tuple(
                self._box_of(JsonFields.object_of(entry, "reference box"), reference_images)
                for entry in JsonFields.list_of(manifest.get("reference_boxes"), "reference_boxes")
            ),
            reference_pixels=reference_pixels,
        )

    def write(self, class_set: ClassSet) -> None:
        """
        Write the class set, replacing the file.

        Parameters
        ----------
        class_set : ClassSet
            Classes, reference boxes and reference pixels to store.

        Raises
        ------
        OSError
            If the file cannot be written.
        """
        reference_images: tuple[ReferenceImage, ...] = class_set.reference_images
        manifest: dict[str, JsonValue] = {
            "format": self.FORMAT_NAME,
            "version": self.FORMAT_VERSION,
            "classes": [
                {"name": definition.name, "phrases": list(definition.text_queries)} for definition in class_set.classes
            ],
            "reference_images": [
                {"name": image.name, "digest": image.digest, "file": self._image_file_of(image)}
                for image in reference_images
            ],
            "reference_boxes": [
                {
                    "class_name": box.class_name,
                    "image": reference_images.index(box.reference_image),
                    "xyxy": list(box.xyxy),
                }
                for box in class_set.reference_boxes
            ],
        }
        partial_path: Path = self._path.with_name(self._path.name + self.PARTIAL_SUFFIX)
        try:
            with zipfile.ZipFile(partial_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(self.MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))
                written_files: set[str] = set()
                for image in reference_images:
                    image_file: str = self._image_file_of(image)
                    if image_file in written_files:
                        continue
                    archive.writestr(
                        image_file,
                        self._png_bytes_of(class_set.reference_pixels[image]),
                        compress_type=zipfile.ZIP_STORED,
                    )
                    written_files.add(image_file)
            partial_path.replace(self._path)
        finally:
            partial_path.unlink(missing_ok=True)

    def _require_format(self, manifest: dict[str, JsonValue]) -> None:
        if manifest.get("format") != self.FORMAT_NAME:
            raise ValueError(f"{self._path.name} is not an OVD GUI class set.")
        version: JsonValue = manifest.get("version")
        if not isinstance(version, int) or version > self.FORMAT_VERSION:
            raise ValueError(f"{self._path.name} has the unsupported class set version {version!r}.")

    def _read_image(self, archive: zipfile.ZipFile, entry: dict[str, JsonValue]) -> tuple[ReferenceImage, Image.Image]:
        reference_image: ReferenceImage = ReferenceImage(
            name=JsonFields.string_of(entry.get("name"), "reference image name"),
            digest=JsonFields.string_of(entry.get("digest"), "reference image digest"),
        )
        with Image.open(
            io.BytesIO(archive.read(JsonFields.string_of(entry.get("file"), "reference image file")))
        ) as source:
            pixels: Image.Image = source.convert("RGB")
        if ReferenceImage.digest_of(pixels) != reference_image.digest:
            raise ValueError(f"Pixels of the reference image '{reference_image.name}' do not match their digest.")
        return reference_image, pixels

    def _class_of(self, entry: dict[str, JsonValue]) -> ClassDefinition:
        return ClassDefinition(
            name=JsonFields.string_of(entry.get("name"), "class name"),
            text_queries=tuple(
                JsonFields.string_of(phrase, "phrase") for phrase in JsonFields.list_of(entry.get("phrases"), "phrases")
            ),
        )

    def _box_of(self, entry: dict[str, JsonValue], reference_images: list[ReferenceImage]) -> ReferenceBox:
        image_index: JsonValue = entry.get("image")
        if (
            not isinstance(image_index, int)
            or isinstance(image_index, bool)
            or not (0 <= image_index < len(reference_images))
        ):
            raise ValueError(f"Reference box image must index reference_images. got {image_index!r}")
        corners: list[float] = [
            JsonFields.number_of(corner, "reference box corner")
            for corner in JsonFields.list_of(entry.get("xyxy"), "xyxy")
        ]
        if len(corners) != 4:
            raise ValueError(f"Reference box xyxy must hold 4 numbers. got {corners}")
        left, top, right, bottom = corners
        return ReferenceBox(
            reference_image=reference_images[image_index],
            class_name=JsonFields.string_of(entry.get("class_name"), "reference box class_name"),
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        )

    def _image_file_of(self, reference_image: ReferenceImage) -> str:
        return f"{self.IMAGE_DIRECTORY}/{reference_image.digest}.png"

    @staticmethod
    def _png_bytes_of(image: Image.Image) -> bytes:
        buffer: io.BytesIO = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
