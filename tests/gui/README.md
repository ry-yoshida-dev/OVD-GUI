# gui

## Overview

Tests of `ovd_gui.gui`, run with an offscreen-capable `QApplication`.

## Components

| Component | Description |
| --------- | ----------- |
| [conftest.py](./conftest.py) | `application` fixture shared by every Qt test. |
| [test_main_window.py](./test_main_window.py) | Background detection of every open image, shown image first, skipping unreadable and failed images and yielding to Detect All and to newer images, Detect All over every image in the background with cancellable status bar progress, opening the image of a selected row, stored and cleared results, results kept per model and shown again without detecting, matched queries, boxes following the table and rejections, class minimums, closing and browsing images, exporting kept results, restoring saved results and comparing models. |
| [test_class_palette.py](./test_class_palette.py) | Class colors. |
| [test_export_dialog.py](./test_export_dialog.py) | Export dialog: confidence availability per format and the output directory requirement. |
| [prompt/](./prompt/README.md) | Class editor and reference image dialog. |
| [sidebar/](./sidebar/README.md) | Collapsible sections, settings and the image list. |
| [viewer/](./viewer/README.md) | Image canvas. |
| [table/](./table/README.md) | Detection table. |
| [statistics/](./statistics/README.md) | Statistics window. |
| [execution/](./execution/README.md) | Batch detection on the worker. |
