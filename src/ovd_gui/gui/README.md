# gui

## Overview

PySide6 widgets of the application. `MainWindow` composes the sidebar (model, classes, images), the image viewer and
the detection table, and reacts to the outcomes reported by `DetectionRunner`, which runs inference on a separate
`QThread`. Only `MainWindow` is exported; the sub-packages are imported by their own path.

Sub-packages depend on the domain packages (`detection`, `vocabulary`, `preset`, `export`, `media`) and on
`class_palette`, never on each other, except `prompt` using `viewer` for its box-drawing dialog.

## Components

| Component | Description |
| --------- | ----------- |
| [main_window.py](./main_window.py) | `MainWindow`: layout, toolbar, stored results per image, Detect All and export, drag and drop. |
| [class_palette.py](./class_palette.py) | `ClassPalette`: stable color per class id, shared by every view. |
| [export_dialog.py](./export_dialog.py) | `ExportDialog`: format, output directory and confidence choice for detecting every image and exporting. |
| [prompt/](./prompt/README.md) | Class editor: classes, phrases and reference images, class sets. |
| [sidebar/](./sidebar/README.md) | Collapsible sidebar sections: model settings and the image list. |
| [viewer/](./viewer/README.md) | Zoomable image view with detection and reference boxes. |
| [table/](./table/README.md) | Detection table: filtering, sorting and selecting detections across images. |
| [intake/](./intake/README.md) | Drop zone and drag-over overlay for adding images. |
| [execution/](./execution/README.md) | Worker thread, single and batch detection runs, batch progress. |
