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
| [test_result_archive.py](./test_result_archive.py) | Round trip of results, prompts with image prompts and rejected detections through a results archive; results of changed or missing image files are dropped. |
| [test_class_threshold_store.py](./test_class_threshold_store.py) | Remembered minimum confidence per class, and unreadable files. |
| [test_session_store.py](./test_session_store.py) | Remembered open images and shown image, and unreadable files. |
