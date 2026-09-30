# workspace

## Overview

Application layer independent of any user interface. `Workspace` holds everything the user works on (open images,
classes, model settings, stored results) and drives the detections: background detection of open images without an
up-to-date result, Detect, Detect All, Update Outdated and export. The web server builds on it; the desktop window
shares only its image and batch types so far and keeps its own copy of the detection flow.

The workspace lives on one owning thread (the asyncio event loop of the web server). Blocking work runs elsewhere and
comes back through a `TaskScheduler`, so the workspace needs no locks. Views subscribe as `WorkspaceObserver`s and
are told which `WorkspaceTopic`s changed and which `Notice`s to show. Requests are answered with an `ActionReply`:
done, refused with a reason, or waiting for the user to approve leaving out reference-only classes.

## Components

| Component | Description |
| --------- | ----------- |
| [workspace.py](./workspace.py) | `Workspace`: open images, classes, model selection, results per detector profile, reviewing and class minimums, background and foreground detection, export, and saving everything shortly after each change. |
| [workspace_stores.py](./workspace_stores.py) | `WorkspaceStores`: data directory stores the workspace reads at start and writes after changes. |
| [workspace_observer.py](./workspace_observer.py) | `WorkspaceObserver`: protocol of a view told about changed topics and notices. |
| [workspace_topic.py](./workspace_topic.py) | `WorkspaceTopic`: part of the workspace that changed. |
| [task_scheduler.py](./task_scheduler.py) | `TaskScheduler`: protocol for running callbacks on the owning thread, delayed calls and blocking work. |
| [scheduled_call.py](./scheduled_call.py) | `ScheduledCall`: protocol of a delayed callback that can be cancelled. |
| [detection_engine.py](./detection_engine.py) | `DetectionEngine`: runs requested detections on a worker thread, one foreground run at a time, with background detections that always yield. |
| [detection_listener.py](./detection_listener.py) | `DetectionListener`: protocol receiving what the `DetectionEngine` reports. |
| [class_workbench.py](./class_workbench.py) | `ClassWorkbench`: classes with their phrases and reference images, edited by class id, and the class set they were loaded from or saved to. |
| [prompt_preparation.py](./prompt_preparation.py) | `PromptPreparation`: prompt built from the classes, or why none could be built and which classes need approval. |
| [model_selector.py](./model_selector.py) | `ModelSelector`: presets that can be chosen and the detector settings of a preset with its overrides. |
| [model_selection.py](./model_selection.py) | `ModelSelection`: chosen preset with device, precision and threshold overrides. |
| [batch_job.py](./batch_job.py) | `BatchJob`: batch detection with the reason it runs and, for an export, where results are written. |
| [batch_purpose.py](./batch_purpose.py) | `BatchPurpose`: Detect All or export. |
| [run_progress.py](./run_progress.py) | `RunProgress`: title, processed and total counts of the running batch, and whether it blocks the user. |
| [export_plan.py](./export_plan.py) | `ExportPlan`: model, image and pending counts of an export, or why it cannot start. |
| [export_request.py](./export_request.py) | `ExportRequest`: export options with the detections listed in the table. |
| [export_writer.py](./export_writer.py) | `ExportWriter`: writes annotation files and optional images with boxes drawn, off the owning thread. |
| [export_report.py](./export_report.py) | `ExportReport`: format, output directory and counts of what an export wrote. |
| [image_state.py](./image_state.py) | `ImageState`: detected, outdated, failed or not analyzed with the shown model. |
| [image_status.py](./image_status.py) | `ImageStatus`: state of one open image with its kept and stored detection counts. |
| [upload_store.py](./upload_store.py) | `UploadStore`: image files sent from a browser, kept under `ovd_gui_data/uploads/`; the same content reuses the stored copy, different content of the same name gets a numbered name. |
| [action_reply.py](./action_reply.py) | `ActionReply`: answer to a request, with the refusal reason or the classes to approve skipping. |
| [action_status.py](./action_status.py) | `ActionStatus`: done, refused or needs approval. |
| [notice.py](./notice.py) | `Notice`: message for the user with its level and title. |
| [notice_level.py](./notice_level.py) | `NoticeLevel`: passing status or error to acknowledge. |

## Examples

```python
workspace = Workspace(ModelSelector(PresetCatalog.from_package(), DeviceAvailability.detect()), stores, scheduler)
workspace.add_observer(view)
workspace.open_paths([Path("images/")])
workspace.edit_classes(lambda bench: bench.set_classes((ClassDefinition.parse("car: car, suv"),)))
reply: ActionReply = workspace.detect_all(is_skipping_approved=False)
workspace.shutdown()
```
