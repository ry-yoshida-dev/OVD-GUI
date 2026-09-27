# prompt

## Overview

Editing of what the model is asked to find: classes, the phrases querying each class, and reference images used as
image prompts. The class list is remembered in the data directory after every change; classes, phrases and reference
images together can be saved and loaded as named class sets.

## Components

| Component | Description |
| --------- | ----------- |
| [class_editor.py](./class_editor.py) | `ClassEditor`: `Set` drop-down loading the saved class sets (with an `Edited` mark and a `Save…` button; loads confirm before discarding unsaved classes) above a class tree under an explorer-style toolbar (`+ Text` adding a class or prompt row next to the selection, `+ Image` opening a drop window for reference images, a trash button, a three-dot menu for the class set library, opening a class file and a confirmed clear; class sets carry the reference images) and a context menu with explicit new class and new prompt actions; remembers the classes. |
| [class_set_dialog.py](./class_set_dialog.py) | `ClassSetDialog`: library of saved class sets with search, preview, load, in-place rename (F2), confirmed delete (Delete), import and export; unreadable sets stay listed so they can be deleted. |
| [class_set_row_delegate.py](./class_set_row_delegate.py) | `ClassSetRowDelegate`: two-line rounded list row with set name, save time and a muted content line. |
| [class_set_preview.py](./class_set_preview.py) | `ClassSetPreview`: name, counts, classes with text prompts and image prompt thumbnails of one class set. |
| [reference_thumbnail.py](./reference_thumbnail.py) | `ReferenceThumbnail`: rounded tile of a reference image with its boxes outlined in the class color. |
| [class_tree.py](./class_tree.py) | `ClassTree`: classes with their phrases and reference images as child rows; new rows are inserted next to the selection and named in place, rows are renamed in place and removed by key, and query rows are dragged to another class or out into classes of their own. |
| [query_drop_target.py](./query_drop_target.py) | `QueryDropTarget`: class and position a dragged query row lands on. |
| [query_drop_kind.py](./query_drop_kind.py) | `QueryDropKind`: whether a dropped query joins a class or becomes a new class. |
| [placeholder_item_delegate.py](./placeholder_item_delegate.py) | `PlaceholderItemDelegate`: item delegate showing a hint in the editor of a row being named. |
| [reference_image_importer.py](./reference_image_importer.py) | `ReferenceImageImporter`: takes reference images from the source dialog and adds the boxes drawn on each to the reference board. |
| [reference_source_dialog.py](./reference_source_dialog.py) | `ReferenceSourceDialog`: drop target for reference images and folders, with buttons opening the file and folder dialogs. |
| [reference_image_dialog.py](./reference_image_dialog.py) | `ReferenceImageDialog`: boxes the examples of a class on a reference image, with drawn boxes movable and resizable, or uses the whole image. |
| [more_icon.py](./more_icon.py) | `MoreIcon`: three-dot icon of the overflow menu button. |
| [trash_icon.py](./trash_icon.py) | `TrashIcon`: trash can icon of the remove action. |
