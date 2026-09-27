# execution

## Overview

Detection off the GUI thread. `DetectionRunner` owns the worker thread, allows one foreground run (Detect, Detect
All, export) at a time, and reports each batch result together with the `BatchJob` it belongs to. Background
detections of the shown image always yield: a foreground run starts as soon as the image being inferred is done,
only the latest waiting background detection is kept, and an image of a running batch can be moved to the front. `BatchProgressDialog` and `RunProgressIndicator` follow the
runner on their own: blocking batches (export) show the modal dialog, while Detect All runs in the background with
its progress and Cancel button in the status bar.

## Components

| Component | Description |
| --------- | ----------- |
| [detection_runner.py](./detection_runner.py) | `DetectionRunner`: queues foreground single and batch detections and yielding background detections to the worker thread, and tracks the busy state and running batch. |
| [detection_worker.py](./detection_worker.py) | `DetectionWorker`: runs `DetectorSession` on the worker thread for one image or a cancellable, reorderable batch, and reports results or errors. |
| [batch_job.py](./batch_job.py) | `BatchJob`: batch request with its purpose, and the export options of an export. |
| [batch_purpose.py](./batch_purpose.py) | `BatchPurpose`: whether a batch detection serves Detect All or an export, and whether it blocks the window. |
| [batch_progress_dialog.py](./batch_progress_dialog.py) | `BatchProgressDialog`: window-modal, cancellable progress of a blocking batch. |
| [run_progress_indicator.py](./run_progress_indicator.py) | `RunProgressIndicator`: status bar progress of any run, with a Cancel button for background batches. |

## Examples

```python
runner: DetectionRunner = DetectionRunner(window)
BatchProgressDialog(runner, window)
window.statusBar().addPermanentWidget(RunProgressIndicator(runner))
runner.batch_finished.connect(on_batch_finished)
runner.detect_in_background(shown_image_request)
runner.detect_batch(BatchJob.detect_all(request))
runner.prioritize(shown_image_path)
```
