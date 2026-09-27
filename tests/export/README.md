# export

## Overview

Tests of `ovd_gui.export`.

## Components

| Component | Description |
| --------- | ----------- |
| [test_detection_archive.py](./test_detection_archive.py) | Recording results per image and exporting them to annotation formats. |
| [test_export_selection.py](./test_export_selection.py) | Exported detections: rejected, below-minimum and unlisted detections left out. |
| [test_annotated_image_writer.py](./test_annotated_image_writer.py) | Boxes drawn in class colors, numbered duplicate names, source images never overwritten. |
| [test_detection_table_writer.py](./test_detection_table_writer.py) | One CSV row per detection with prompt, box and kept state, in the given order. |
