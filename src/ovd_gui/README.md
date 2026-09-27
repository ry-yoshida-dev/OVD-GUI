# ovd_gui

## Overview

GUI application for open-vocabulary detection with model presets switchable at run time.

## Components

| Component | Description |
| --------- | ----------- |
| [\_\_main\_\_.py](./__main__.py) | `main`: launches the application, opening images given as arguments. |
| [preset/](./preset/README.md) | Discovery of YAML model presets and their conversion into `DetectorSettings`. |
| [detection/](./detection/README.md) | Detector lifecycle (load, reuse, switch), prompts built from classes and reference images, and detection request/outcome types. |
| [vocabulary/](./vocabulary/README.md) | Classes and their phrases, remembered between runs and read from or written to text files. |
| [storage/](./storage/README.md) | Named class sets saved as self-contained archives holding classes, phrases, reference boxes and reference image pixels. |
| [export/](./export/README.md) | Export of per-image results to COCO, YOLO, Pascal VOC, LabelMe and Create ML. |
| [media/](./media/README.md) | Image files: EXIF-upright loading and gathering images from dropped or chosen paths. |
| [gui/](./gui/README.md) | Qt widgets: main window composing the sidebar, image viewer, result table and background detection. |
