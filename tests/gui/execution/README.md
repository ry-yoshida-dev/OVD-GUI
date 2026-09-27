# execution

## Overview

Tests of `ovd_gui.gui.execution`.

## Components

| Component | Description |
| --------- | ----------- |
| [test_detection_runner.py](./test_detection_runner.py) | Scheduling of foreground, background and batch runs: waiting and dropped background requests, rejected runs, failures, prioritized images and cancellation. |
| [test_detection_worker.py](./test_detection_worker.py) | Detection on the worker: image files read there, unreadable files and unexpected errors reported, batch cancellation and prioritized images. |
