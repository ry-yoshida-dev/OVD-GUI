# execution

## Overview

Tests of `ovd_gui.gui.execution`.

## Components

| Component | Description |
| --------- | ----------- |
| [test_detection_runner.py](./test_detection_runner.py) | Scheduling of foreground, background and batch runs: waiting and dropped background requests, rejected runs, failures, prioritized images and cancellation. |
| [test_detection_worker.py](./test_detection_worker.py) | Batch detection on the worker: skipped unreadable files, cancellation and prioritized images. |
