# workspace

## Overview

Tests of `ovd_gui.workspace`, run without Qt or a web server: a manual `TaskScheduler` runs the callbacks handed back
from the worker thread, and a stub detector returns boxes without model weights.

## Components

| Component | Description |
| --------- | ----------- |
| [conftest.py](./conftest.py) | Stub detector, manual scheduler, recording observer and a workspace over a temporary data directory. |
| [test_workspace.py](./test_workspace.py) | Background detection shown image first, outdated results after class edits, Detect All progress and refusals, approval of reference-only classes, failure notices, kept counts, closing images, restored sessions (also when the shown image was deleted), delayed saving, export, listed-only export refused while images are pending, and pinned profiles. |
| [test_detection_engine.py](./test_detection_engine.py) | Foreground runs waiting for the background detection in progress, cancelled batches, and the engine idle again when the listener raises. |
| [test_model_selector.py](./test_model_selector.py) | Preset values, overrides, float16 and device validation, and threshold ranges. |
| [test_upload_store.py](./test_upload_store.py) | Uploaded folders kept inside the upload directory, reused copies, numbered names and paths leading outside dropped. |
