# execution

## Overview

Detection off the GUI thread. `DetectionRunner` owns the worker thread, allows one run at a time, and reports each
batch result together with the `BatchJob` it belongs to; `BatchProgressDialog` follows the runner on its own.

## Components

| Component | Description |
| --------- | ----------- |
| [detection_runner.py](./detection_runner.py) | `DetectionRunner`: queues single and batch detections to the worker thread and tracks the busy state and running batch. |
| [detection_worker.py](./detection_worker.py) | `DetectionWorker`: runs `DetectorSession` on the worker thread for one image or a cancellable batch, and reports results or errors. |
| [batch_job.py](./batch_job.py) | `BatchJob`: batch request with its purpose, and the export options of an export. |
| [batch_purpose.py](./batch_purpose.py) | `BatchPurpose`: whether a batch detection serves Detect All or an export. |
| [batch_progress_dialog.py](./batch_progress_dialog.py) | `BatchProgressDialog`: cancellable progress of the running batch. |

## Examples

```python
runner: DetectionRunner = DetectionRunner(window)
BatchProgressDialog(runner, window)
runner.batch_finished.connect(on_batch_finished)
runner.detect_batch(BatchJob.detect_all(request))
```
