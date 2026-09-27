# storage

## Overview

Tests of `ovd_gui.storage`.

## Components

| Component | Description |
| --------- | ----------- |
| [test_class_set.py](./test_class_set.py) | Capturing classes and their reference boxes from a board, and rejecting inconsistent sets. |
| [test_class_set_archive.py](./test_class_set_archive.py) | Round trip of classes, boxes and pixels through a `.ovdset` archive; foreign, malformed and tampered archives. |
| [test_class_set_summary.py](./test_class_set_summary.py) | One-line description of a class set's counts. |
| [test_class_set_store.py](./test_class_set_store.py) | Named class sets in the data directory: listing with summaries, deleting, renaming, importing and exporting, unusable names. |
