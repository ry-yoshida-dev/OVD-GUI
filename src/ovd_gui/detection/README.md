# detection

## Overview

Qt-independent detection logic: keeps one loaded detector and switches it only when the model changes, builds the
prompt from the classes, their phrases and user-drawn reference boxes, and remembers the latest result of every image.

Every class is queried by each of its phrases and, when the model takes image prompts, by each of its reference
images (the boxes of one image are averaged into one query). A `LabeledPrompt` names every query, so a detection
reports the phrase or reference image that matched it.

## Components

| Component | Description |
| --------- | ----------- |
| [detector_session.py](./detector_session.py) | `DetectorSession`: loads the requested model, reusing it when only thresholds or batch size differ. |
| [detection_request.py](./detection_request.py) | `DetectionRequest`: settings, image and labeled prompt of one run. |
| [batch_detection_request.py](./batch_detection_request.py) | `BatchDetectionRequest`: settings, labeled prompt and image files of a batch run, cancellable from any thread. |
| [batch_detection_summary.py](./batch_detection_summary.py) | `BatchDetectionSummary`: detected count, skipped unreadable files and whether the batch was cancelled. |
| [reference_box.py](./reference_box.py) | `ReferenceBox`: box drawn on an image around an example of a class. |
| [reference_board.py](./reference_board.py) | `ReferenceBoard`: reference boxes per class and image; builds the `LabeledPrompt` of the classes, one visual query per reference image, reusing unchanged `VisualReference`s. |
| [labeled_prompt.py](./labeled_prompt.py) | `LabeledPrompt`: `Prompt` with a display label per query (phrase or reference image name). |
| [detection_outcome.py](./detection_outcome.py) | `DetectionOutcome`: result, inference time and whether the model was reloaded. |
| [detection_catalog.py](./detection_catalog.py) | `DetectionCatalog`: latest result and query labels per image, listed as individual detections for searching across images. |
| [detection_filter.py](./detection_filter.py) | `DetectionFilter`: class, file-name and confidence conditions for listing detections and images without detections. |
| [detection_record.py](./detection_record.py) | `DetectionRecord`: one detection with its image path, index in that image's result and matched query label. |
