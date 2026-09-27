# detection

## Overview

Qt-independent detection logic: keeps one loaded detector and switches it only when the model changes, builds the
prompt from the classes, their phrases and user-drawn reference boxes, and remembers the latest result of every image
for every detector profile (model, device, precision and thresholds), so results of several models can be compared.

Every class is queried by each of its phrases and, when the model takes image prompts, by each of its reference
images (the boxes of one image are averaged into one query). A `LabeledPrompt` names every query, so a detection
reports the phrase or reference image that matched it.

## Components

| Component | Description |
| --------- | ----------- |
| [detector_session.py](./detector_session.py) | `DetectorSession`: loads the requested model, reusing it when only thresholds or batch size differ. |
| [device_availability.py](./device_availability.py) | `DeviceAvailability`: GPU backends of this machine, probed once at start: which devices can be requested and on which float16 can run. |
| [detection_request.py](./detection_request.py) | `DetectionRequest`: settings, image with its file path, and labeled prompt of one run. |
| [batch_detection_request.py](./batch_detection_request.py) | `BatchDetectionRequest`: settings, labeled prompt and image files of a batch run, cancellable and reorderable from any thread. |
| [image_queue.py](./image_queue.py) | `ImageQueue`: thread-safe queue of the images a batch has yet to detect, where one image can be moved to the front. |
| [batch_detection_summary.py](./batch_detection_summary.py) | `BatchDetectionSummary`: detected count, skipped unreadable files and whether the batch was cancelled. |
| [reference_image.py](./reference_image.py) | `ReferenceImage`: identity of a reference image by display name and pixel SHA-256, independent of any file path. |
| [reference_box.py](./reference_box.py) | `ReferenceBox`: box drawn on a reference image around an example of a class. |
| [reference_board.py](./reference_board.py) | `ReferenceBoard`: reference boxes per class and image with the pixels of every boxed image, replaceable at once when a class set is loaded; builds the `LabeledPrompt` of the classes, one visual query per reference image, reusing unchanged `VisualReference`s; lists the reference-only classes a text-only model cannot query. |
| [labeled_prompt.py](./labeled_prompt.py) | `LabeledPrompt`: `Prompt` with a display label per query (phrase or reference image name). |
| [detection_outcome.py](./detection_outcome.py) | `DetectionOutcome`: result, inference time and whether the model was reloaded. |
| [detector_profile.py](./detector_profile.py) | `DetectorProfile`: model, device, precision and thresholds a result was detected with; equal for runs differing only in batch size. |
| [result_library.py](./result_library.py) | `ResultLibrary`: one `DetectionCatalog` per detector profile, in the order the profiles were added. |
| [profile_summary.py](./profile_summary.py) | `ProfileSummary`: image and detection counts of one profile. |
| [detection_catalog.py](./detection_catalog.py) | `DetectionCatalog`: latest result and query labels per image, listed as individual detections for searching across images. |
| [detection_record.py](./detection_record.py) | `DetectionRecord`: one detection with its image path, index in that image's result and matched query label. |
