# prompt

## Overview

Tests of `ovd_gui.gui.prompt`.

## Components

| Component | Description |
| --------- | ----------- |
| [test_class_editor.py](./test_class_editor.py) | Class tree: adding rows next to the selection and naming them in place, rejected and cancelled entries, dragging queries between classes and into new classes, in-place edits, removing classes with the trash button, phrases and reference images, adding reference images, saving and loading class sets with their reference images, loading from the class set library and the `Set` drop-down, confirming before edits are discarded. |
| [test_class_set_dialog.py](./test_class_set_dialog.py) | Class set library: listing and previewing sets, searching, loading, renaming in place, confirmed deletion and unreadable sets. |
| [test_reference_image_dialog.py](./test_reference_image_dialog.py) | Boxes drawn on a reference image and adjusted afterwards, or the whole image without boxes. |
| [test_reference_source_dialog.py](./test_reference_source_dialog.py) | Reference images taken from dropped files and folders, and drops without supported images. |
