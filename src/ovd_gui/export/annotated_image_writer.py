from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from open_vocabulary_detector import DetectionResult
from PIL import Image, ImageColor, ImageDraw, ImageFont

from ..media import LoadedImage


class AnnotatedImageWriter:
    """
    Images saved with their detections drawn, for looking through the results outside the application.

    Each box is outlined in the color of its class and labeled with the class name, optionally followed by the
    confidence; line width and label size grow with the image. Files keep the name and format of their source in the
    output directory; a name already written by this writer gets a number, e.g. ``photo_2.jpg``.
    """

    REFERENCE_IMAGE_SIDE: ClassVar[float] = 1000.0
    BASE_LINE_WIDTH: ClassVar[float] = 2.0
    BASE_FONT_SIZE: ClassVar[float] = 16.0
    MINIMUM_FONT_SIZE: ClassVar[float] = 12.0
    JPEG_SUFFIXES: ClassVar[frozenset[str]] = frozenset({".jpg", ".jpeg"})
    JPEG_QUALITY: ClassVar[int] = 95
    LIGHT_COLOR_LUMINANCE: ClassVar[float] = 0.6

    def __init__(self, class_colors: Sequence[str], is_confidence_shown: bool, output_directory: Path) -> None:
        """
        Parameters
        ----------
        class_colors : Sequence[str]
            Colors such as ``"#e6194b"``, cycled through by class id.
        is_confidence_shown : bool
            Whether labels include the confidence.
        output_directory : Path
            Directory receiving the images, created when the first image is written.

        Raises
        ------
        ValueError
            If ``class_colors`` is empty.
        """
        if not class_colors:
            raise ValueError("class_colors must not be empty")
        self._class_colors: tuple[tuple[int, ...], ...] = tuple(ImageColor.getrgb(color) for color in class_colors)
        self._is_confidence_shown: bool = is_confidence_shown
        self._output_directory: Path = output_directory
        self._written_names: set[str] = set()

    def write(self, image: LoadedImage, result: DetectionResult) -> Path:
        """
        Draw detections over an image and save it.

        Parameters
        ----------
        image : LoadedImage
            Upright image the detections were found in.
        result : DetectionResult
            Detections to draw, in pixels of ``image``.

        Returns
        -------
        Path
            Written file.

        Raises
        ------
        ValueError
            If the file to write is the source image itself.
        OSError
            If the directory or the file cannot be written.
        """
        target_path: Path = self._output_directory / self._unique_name(image.path)
        if target_path.resolve() == image.path.resolve():
            raise ValueError(f"writing {target_path} would overwrite the source image")
        annotated: Image.Image = self._draw(image.image, result)
        self._output_directory.mkdir(parents=True, exist_ok=True)
        if target_path.suffix.lower() in self.JPEG_SUFFIXES:
            annotated.save(target_path, quality=self.JPEG_QUALITY)
        else:
            annotated.save(target_path)
        return target_path

    def _draw(self, source: Image.Image, result: DetectionResult) -> Image.Image:
        annotated: Image.Image = source.copy()
        scale: float = max(annotated.size) / self.REFERENCE_IMAGE_SIDE
        line_width: int = max(1, round(self.BASE_LINE_WIDTH * scale))
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.load_default(
            size=max(self.MINIMUM_FONT_SIZE, self.BASE_FONT_SIZE * scale)
        )
        padding: int = max(1, line_width)
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(annotated)
        for detection in result:
            color: tuple[int, ...] = self._class_colors[detection.class_id % len(self._class_colors)]
            x_min, y_min, x_max, y_max = (float(value) for value in detection.box.value.tolist())
            draw.rectangle((x_min, y_min, x_max, y_max), outline=color, width=line_width)
            text: str = (
                f"{detection.class_name} {detection.confidence:.2f}"
                if self._is_confidence_shown
                else detection.class_name
            )
            text_left, text_top, text_right, text_bottom = draw.textbbox((0, 0), text, font=font)
            label_height: float = text_bottom - text_top + 2 * padding
            label_top: float = y_min - label_height if y_min >= label_height else y_min
            draw.rectangle(
                (x_min, label_top, x_min + text_right - text_left + 2 * padding, label_top + label_height), fill=color
            )
            draw.text(
                (x_min + padding - text_left, label_top + padding - text_top),
                text,
                fill=self._text_color_on(color),
                font=font,
            )
        return annotated

    def _unique_name(self, image_path: Path) -> str:
        name: str = image_path.name
        number: int = 1
        while name.casefold() in self._written_names:
            number += 1
            name = f"{image_path.stem}_{number}{image_path.suffix}"
        self._written_names.add(name.casefold())
        return name

    @classmethod
    def _text_color_on(cls, background: tuple[int, ...]) -> tuple[int, int, int]:
        red, green, blue = (channel / 255.0 for channel in background[:3])
        luminance: float = 0.299 * red + 0.587 * green + 0.114 * blue
        return (0, 0, 0) if luminance > cls.LIGHT_COLOR_LUMINANCE else (255, 255, 255)
