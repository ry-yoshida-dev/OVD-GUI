# ovd_gui

## Overview

Web and desktop GUI for open-vocabulary detection with model presets switchable at run time. The web interface
starts by default and is built on the Qt-free `workspace` package; the PySide6 window starts with `--qt`.

## Components

| Component | Description |
| --------- | ----------- |
| [\_\_main\_\_.py](./__main__.py) | `main`: starts the web server, or the desktop window with `--qt`, opening images given as arguments. |
| [cli/](./cli/README.md) | Command-line arguments: interface, paths, host, port and browser opening. |
| [preset/](./preset/README.md) | Discovery of YAML model presets and their conversion into `DetectorSettings`. |
| [detection/](./detection/README.md) | Detector lifecycle (load, reuse, switch), prompts built from classes and reference images, and detection request/outcome types. |
| [vocabulary/](./vocabulary/README.md) | Classes and their phrases, remembered between runs and read from or written to text files. |
| [storage/](./storage/README.md) | Named class sets saved as self-contained archives holding classes, phrases, reference boxes and reference image pixels. |
| [export/](./export/README.md) | Export of per-image results to COCO, YOLO, Pascal VOC, LabelMe and Create ML. |
| [media/](./media/README.md) | Image files: EXIF-upright loading, gathering images from dropped or chosen paths, and class colors. |
| [analysis/](./analysis/README.md) | Statistics over stored results: per-class counts and confidences, and class-by-class comparison of two detector profiles. |
| [review/](./review/README.md) | Minimum confidence of each class deciding which stored detections are kept, without detecting again. |
| [workspace/](./workspace/README.md) | Application layer independent of any user interface: open images, classes, model selection, results, detection runs, uploads and export. |
| [web/](./web/README.md) | FastAPI server: JSON API over the workspace, change events over a WebSocket, and the built single-page frontend. |
| [gui/](./gui/README.md) | Optional PySide6 desktop window (`--qt`): main window composing the sidebar, image viewer, result table and background detection. |
