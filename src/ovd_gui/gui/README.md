# gui

## Overview

PySide6 desktop window, started by `ovd-gui --qt` through `QtLauncher` and requiring the `qt` extra. `MainWindow` composes the sidebar (model, classes, images), the image viewer and
the detection table, and reacts to the outcomes reported by `DetectionRunner`, which runs inference on a separate
`QThread`. Only `MainWindow` and `QtLauncher` are exported; the sub-packages are imported by their own path.

Sub-packages depend on the domain packages (`detection`, `vocabulary`, `storage`, `preset`, `export`, `media`,
`review`, `analysis`), on `workspace` for the types shared with the web interface (`BatchJob`, `BatchPurpose`,
`ImageState`, `ImageStatus`) and on `class_palette`, never on each other, except `prompt` using `viewer` for its box-drawing dialog.

## Components

| Component | Description |
| --------- | ----------- |
| [qt_launcher.py](./qt_launcher.py) | `QtLauncher`: creates the `QApplication` and the main window over the stores of the working directory, opening the given paths or the last session. |
| [main_window.py](./main_window.py) | `MainWindow`: layout, toolbar, stored results per model and image, switching the shown model, background detection of the image `BackgroundQueue` picks, outdated results after class edits, background Detect All, export of the kept results with optional images with boxes drawn, reviewing and class minimums, statistics and model comparison, closing and browsing images, saving and restoring results and the open images, drag and drop. |
| [class_palette.py](./class_palette.py) | `ClassPalette`: stable color per class id, shared by every view. |
| [export_dialog.py](./export_dialog.py) | `ExportDialog`: format, output directory, confidence choice, exported detections, minimum confidence and saving images with boxes drawn. |
| [prompt/](./prompt/README.md) | Class editor: classes, phrases and reference images, class sets. |
| [sidebar/](./sidebar/README.md) | Collapsible sidebar sections: model settings and the image list. |
| [viewer/](./viewer/README.md) | Zoomable image view with detection and reference boxes. |
| [table/](./table/README.md) | Detection table: filtering, sorting, keeping or rejecting and selecting detections across images. |
| [statistics/](./statistics/README.md) | Statistics window: per-class counts, confidence histogram, class minimums and model comparison. |
| [intake/](./intake/README.md) | Drop zone and drag-over overlay for adding images. |
| [execution/](./execution/README.md) | Worker thread, single and batch detection runs, batch progress. |
