# tests

## Overview

Unit tests runnable without downloading model weights. The layout mirrors `src/ovd_gui/`; Qt tests share the
`application` fixture of [gui/conftest.py](./gui/conftest.py), and web tests need `httpx` for the FastAPI `TestClient`.

## Components

| Component | Description |
| --------- | ----------- |
| [preset/](./preset/README.md) | Preset discovery and conversion into `DetectorSettings`. |
| [detection/](./detection/README.md) | Detector reuse, stored results and filters, reference boxes and labeled prompts. |
| [vocabulary/](./vocabulary/README.md) | Class definitions, vocabulary uniqueness, class list files and the remembered class list. |
| [storage/](./storage/README.md) | Class sets with reference images, their archive format and named sets in the data directory; saved results and class minimums. |
| [review/](./review/README.md) | Minimum confidence per class. |
| [analysis/](./analysis/README.md) | Per-class statistics, confidence histograms, box pairing and model comparison. |
| [export/](./export/README.md) | Recording results, choosing the exported detections and exporting them to annotation formats. |
| [media/](./media/README.md) | Expansion of dropped files and folders into new images. |
| [workspace/](./workspace/README.md) | The UI-independent workspace, detection engine, model selection and uploads. |
| [web/](./web/README.md) | The web API through the FastAPI test client. |
| [gui/](./gui/README.md) | Widgets, the main window and the detection worker. |

## Examples

```bash
QT_QPA_PLATFORM=offscreen pytest
```
