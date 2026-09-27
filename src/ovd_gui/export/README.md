# export

## Overview

Qt-independent export of detection results to annotation formats (MS COCO, YOLO, Pascal VOC, LabelMe, Create ML)
with [ObjectDetectionFormat](https://github.com/ry-yoshida-dev/ObjectDetectionFormat). The GUI fills the archive by
detecting every open image before writing; boxes are in pixels of the EXIF-upright image.

## Components

| Component | Description |
| --------- | ----------- |
| [detection_archive.py](./detection_archive.py) | `DetectionArchive`: latest result per image, converted to an `AnnotationDataset` and written. |
| [export_options.py](./export_options.py) | `ExportOptions`: format, output directory and confidence setting; builds the matching writer. |

## Examples

```python
from pathlib import Path

from object_detection_format import AnnotationFormat
from ovd_gui.export import DetectionArchive, ExportOptions

archive = DetectionArchive()
archive.record(Path("street.jpg"), result)
archive.write(
    ExportOptions(
        annotation_format=AnnotationFormat.YOLO,
        output_directory=Path("labels"),
        is_confidence_included=True,
    ),
    class_names=("person", "car"),
)
```
