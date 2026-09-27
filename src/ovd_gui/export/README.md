# export

## Overview

Qt-independent export of detection results to annotation formats (MS COCO, YOLO, Pascal VOC, LabelMe, Create ML)
with [ObjectDetectionFormat](https://github.com/ry-yoshida-dev/ObjectDetectionFormat). The GUI exports the stored
results of the shown model: `ExportSelection` leaves out rejected detections, those below the minimum confidence of
their class or of the export, and optionally those not listed in the detection table. Boxes are in pixels of the
EXIF-upright image.

`AnnotatedImageWriter` saves copies of the exported images with their boxes drawn, and `DetectionTableWriter` saves
the detections listed in the detection table as CSV.

## Components

| Component | Description |
| --------- | ----------- |
| [detection_archive.py](./detection_archive.py) | `DetectionArchive`: latest result per image, converted to an `AnnotationDataset` and written. |
| [export_options.py](./export_options.py) | `ExportOptions`: format, output directory, confidence setting, scope, minimum confidence and whether images with boxes are saved; builds the matching writer. |
| [annotated_image_writer.py](./annotated_image_writer.py) | `AnnotatedImageWriter`: images saved with their detections drawn in class colors and labeled, never over the source. |
| [detection_table_writer.py](./detection_table_writer.py) | `DetectionTableWriter`: detections written as a CSV table with image, class, prompt, confidence, box and kept state. |
| [export_scope.py](./export_scope.py) | `ExportScope`: every kept detection, or only those listed in the detection table. |
| [export_selection.py](./export_selection.py) | `ExportSelection`: which stored detections of an image are exported. |

## Examples

```python
from pathlib import Path

from object_detection_format import AnnotationFormat
from ovd_gui.export import DetectionArchive, ExportOptions, ExportSelection
from ovd_gui.review import ClassThresholds

options = ExportOptions(
    annotation_format=AnnotationFormat.YOLO,
    output_directory=Path("labels"),
    is_confidence_included=True,
    minimum_confidence=0.3,
)
selection = ExportSelection(ClassThresholds(0.0, {"car": 0.45}), minimum_confidence=options.minimum_confidence)
archive = DetectionArchive()
for image_path in image_paths:
    selected = selection.selected_result(catalog, image_path)
    if selected is not None:
        archive.record(image_path, selected)
archive.write(options, class_names=("person", "car"))
```
