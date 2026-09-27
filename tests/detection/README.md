# detection

## Overview

Tests of `ovd_gui.detection`.

## Components

| Component | Description |
| --------- | ----------- |
| [test_detector_session.py](./test_detector_session.py) | Model reuse rules of `DetectorSession`. |
| [test_device_availability.py](./test_device_availability.py) | Devices that can be requested, and those on which float16 can run, given the available GPU backends. |
| [test_detection_catalog.py](./test_detection_catalog.py) | Stored results per image as detection records, detection filters, outdated images, rejected detections and removed images. |
| [test_image_queue.py](./test_image_queue.py) | Order of the images taken from an `ImageQueue` and prioritized images. |
| [test_result_library.py](./test_result_library.py) | Detector profiles and results kept apart per profile. |
| [test_background_queue.py](./test_background_queue.py) | Order of background detection, skipped unreadable and failed images, pausing and pinned profiles. |
| [test_prompt_change.py](./test_prompt_change.py) | Prompt signatures per model and the classes added, removed or edited between two prompts. |
| [test_reference_board.py](./test_reference_board.py) | Reference boxes, prompt issues and the labeled prompts built from classes, phrases and reference images. |
