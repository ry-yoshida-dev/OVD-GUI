# prompt

## Overview

Editing of what the model is asked to find: classes, the phrases querying each class, and reference images used as
image prompts. The class list is remembered in the data directory after every change and can be saved and loaded as
named class sets.

## Components

| Component | Description |
| --------- | ----------- |
| [class_editor.py](./class_editor.py) | `ClassEditor`: class tree with the input field, query buttons, and class set save/load; remembers the classes. |
| [class_tree.py](./class_tree.py) | `ClassTree`: classes with their phrases and reference images as child rows, renamed in place and removed by key. |
| [reference_image_importer.py](./reference_image_importer.py) | `ReferenceImageImporter`: picks reference image files and adds the boxes drawn on each to the reference board. |
| [reference_image_dialog.py](./reference_image_dialog.py) | `ReferenceImageDialog`: boxes the examples of a class on a reference image, or uses the whole image. |
