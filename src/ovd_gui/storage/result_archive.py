import io
import json
import weakref
import zipfile
from pathlib import Path
from typing import ClassVar

from open_vocabulary_detector import VisualReference
from PIL import Image

from ..detection import ReferenceImage, ResultLibrary
from .json_fields import JsonFields, JsonValue
from .result_manifest_reader import ResultManifestReader
from .result_manifest_writer import ResultManifestWriter


class ResultArchive:
    """
    Stored detection results of every detector profile, kept in one ZIP file between runs.

    ``manifest.json`` lists the profiles with the result, prompt and rejected detections of every image, and the
    prompts with their queries, labels and signatures; the pixels of every reference image used by a visual query
    are stored losslessly as ``images/<sha256>.png``, so restored results keep their image prompts. Every image
    records the modification time and size of its file when the archive was written; on reading, results of image
    files that are missing or have changed since are dropped. Writing goes through a temporary file, so a failed
    write leaves an existing archive intact.

    ``manifest.json`` looks like::

        {
          "format": "ovd-gui-results",
          "version": 1,
          "reference_images": [{"name": "sedan.jpg", "digest": "<sha256>", "file": "images/<sha256>.png"}],
          "prompts": [{
            "classes": [{"name": "car", "queries": [
              {"text": "car"}, {"references": [{"image": 0, "boxes": [[1, 2, 30, 40]]}]}
            ]}],
            "labels": ["car", "sedan.jpg"],
            "signature": [{"name": "car", "phrases": ["car"], "reference_boxes": [{"image": 0, "xyxy": [1, 2, 30, 40]}]}]
          }],
          "profiles": [{
            "backend": "owl_vit", "weights_path": "...", "device": "auto", "is_half_precision_enabled": false,
            "confidence_threshold": 0.1, "nms_iou_threshold": 0.5,
            "images": [{
              "path": "/data/street.jpg", "modified_ns": 0, "size": 1024, "width": 640, "height": 480, "prompt": 0,
              "boxes": [[10, 20, 110, 220]], "confidences": [0.8], "query_ids": [1], "rejected": []
            }]
          }]
        }

    ``image`` indexes ``reference_images`` and ``prompt`` indexes ``prompts``. A reference image named only by a
    signature, not used by any visual query, has no ``file``.
    """

    SUFFIX: ClassVar[str] = ".ovdresults"
    FORMAT_NAME: ClassVar[str] = "ovd-gui-results"
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
        self._reference_identities: weakref.WeakKeyDictionary[VisualReference, ReferenceImage] = (
            weakref.WeakKeyDictionary()
        )

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

    def write(self, library: ResultLibrary) -> None:
        """
        Write every result of a library, replacing the file.

        Parameters
        ----------
        library : ResultLibrary
            Results to store; images whose file cannot be found are left out.

        Raises
        ------
        OSError
            If the file cannot be written.
        """
        writer: ResultManifestWriter = ResultManifestWriter(self._reference_identities, self._image_file_of)
        manifest: dict[str, JsonValue] = writer.manifest_of(library, self.FORMAT_NAME, self.FORMAT_VERSION)
        partial_path: Path = self._path.with_name(self._path.name + self.PARTIAL_SUFFIX)
        try:
            with zipfile.ZipFile(partial_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(self.MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False))
                for reference_image, pixels in writer.reference_pixels.items():
                    archive.writestr(
                        self._image_file_of(reference_image),
                        self._png_bytes_of(pixels),
                        compress_type=zipfile.ZIP_STORED,
                    )
            partial_path.replace(self._path)
        finally:
            partial_path.unlink(missing_ok=True)

    def read(self) -> ResultLibrary:
        """
        Read the stored results.

        Returns
        -------
        ResultLibrary
            Profiles in stored order with the results of the image files that are unchanged since writing.

        Raises
        ------
        OSError
            If the file cannot be read.
        ValueError
            If the file is not a result archive or its content is invalid.
        """
        try:
            with zipfile.ZipFile(self._path) as archive:
                manifest: dict[str, JsonValue] = JsonFields.object_of(
                    JsonFields.parse(archive.read(self.MANIFEST_NAME).decode("utf-8")), "manifest"
                )
                self._require_format(manifest)
                return ResultManifestReader(archive).library_of(manifest)
        except zipfile.BadZipFile as error:
            raise ValueError(f"{self._path.name} is not a result archive: {error}") from error
        except KeyError as error:
            raise ValueError(f"{self._path.name} lacks an entry: {error}") from error
        except UnicodeDecodeError as error:
            raise ValueError(f"{self.MANIFEST_NAME} of {self._path.name} is not UTF-8 text.") from error
        except json.JSONDecodeError as error:
            raise ValueError(f"{self.MANIFEST_NAME} of {self._path.name} is not valid JSON: {error}") from error
        except TypeError as error:
            raise ValueError(f"{self.MANIFEST_NAME} of {self._path.name} is malformed: {error}") from error

    def _require_format(self, manifest: dict[str, JsonValue]) -> None:
        if manifest.get("format") != self.FORMAT_NAME:
            raise ValueError(f"{self._path.name} is not an OVD GUI result archive.")
        version: JsonValue = manifest.get("version")
        if not isinstance(version, int) or version > self.FORMAT_VERSION:
            raise ValueError(f"{self._path.name} has the unsupported result archive version {version!r}.")

    @classmethod
    def _image_file_of(cls, reference_image: ReferenceImage) -> str:
        return f"{cls.IMAGE_DIRECTORY}/{reference_image.digest}.png"

    @staticmethod
    def _png_bytes_of(image: Image.Image) -> bytes:
        buffer: io.BytesIO = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
