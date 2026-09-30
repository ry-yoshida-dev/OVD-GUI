# schema

## Overview

Pydantic models of the JSON request bodies accepted by the [web](../README.md) API. Enum values, paths and profiles
are sent as strings and converted to domain types by the routes.

## Components

| Component | Description |
| --------- | ----------- |
| [paths_body.py](./paths_body.py) | `PathsBody`: files or directories on the server to open or close. |
| [path_body.py](./path_body.py) | `PathBody`: one file on the server. |
| [text_body.py](./text_body.py) | `TextBody`: typed text, e.g. one class per line. |
| [name_body.py](./name_body.py) | `NameBody`: new name of a class or class set. |
| [class_row_body.py](./class_row_body.py) | `ClassRowBody`: new class, or new phrases of a class, with their position. |
| [phrase_reference.py](./phrase_reference.py) | `PhraseReference`: one phrase of a class. |
| [image_prompt_reference.py](./image_prompt_reference.py) | `ImagePromptReference`: one reference image of a class, by name and pixel digest. |
| [remove_classes_body.py](./remove_classes_body.py) | `RemoveClassesBody`: classes, phrases and reference images removed at once. |
| [move_phrase_body.py](./move_phrase_body.py) | `MovePhraseBody`: phrase dragged to another class, position or a class of its own. |
| [move_reference_body.py](./move_reference_body.py) | `MoveReferenceBody`: reference image dragged to another class. |
| [reference_boxes_body.py](./reference_boxes_body.py) | `ReferenceBoxesBody`: boxes drawn on an opened reference image. |
| [preset_body.py](./preset_body.py) | `PresetBody`: preset chosen with its own values. |
| [model_selection_body.py](./model_selection_body.py) | `ModelSelectionBody`: preset with device, precision and threshold overrides. |
| [approval_body.py](./approval_body.py) | `ApprovalBody`: detection run request with the approval of skipped classes. |
| [profile_body.py](./profile_body.py) | `ProfileBody`: stored detector profile, or none. |
| [detection_reference.py](./detection_reference.py) | `DetectionReference`: one detection of the shown results. |
| [acceptance_body.py](./acceptance_body.py) | `AcceptanceBody`: detections to keep or reject. |
| [table_body.py](./table_body.py) | `TableBody`: detections listed in the table, in display order. |
| [thresholds_body.py](./thresholds_body.py) | `ThresholdsBody`: default and per-class minimum confidence. |
| [export_body.py](./export_body.py) | `ExportBody`: options chosen in the export dialog. |
