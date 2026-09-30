# web

## Overview

FastAPI server of the default user interface. It exposes the [workspace](../workspace/README.md) as a JSON API under
`/api`, pushes changes to every connected browser over the `/api/events` WebSocket, and serves the single-page
interface built from [frontend/](../../../frontend/) into `static/` (a build output, not committed).

The workspace runs on the event loop of the server (`AsyncioTaskScheduler`), which plays the role of the GUI thread;
blocking work runs in the default executor. The browser cannot see the file system of the server, so images are
either uploaded (stored by `UploadStore` under `ovd_gui_data/uploads/`) or picked from server paths listed by
`DirectoryBrowser`. Exports are written on the server, and the last one can be downloaded as a ZIP file.

Errors caused by a request, such as an invalid class name or an unknown image, are answered with status 400 and their
message. The server listens on `127.0.0.1` by default; on a remote machine, forward the port over SSH instead of
listening on every interface. `AccessGuard` lets only browsers that opened the printed address, which carries an
access token created for the run, use the API and the WebSocket.

## Components

| Component | Description |
| --------- | ----------- |
| [web_launcher.py](./web_launcher.py) | `WebLauncher`: builds the stores of the working directory, starts uvicorn and optionally opens the default browser. |
| [access_guard.py](./access_guard.py) | `AccessGuard`: ASGI middleware exchanging the access token of the printed address for a cookie and refusing requests without it. |
| [connection_kind.py](./connection_kind.py) | `ConnectionKind`: HTTP, WebSocket or lifespan ASGI scope. |
| [web_application.py](./web_application.py) | `WebApplication`: FastAPI application creating the workspace on server start, mounting the routes, the event WebSocket and the static frontend. |
| [web_context.py](./web_context.py) | `WebContext`: workspace and helpers shared by the request handlers. |
| [asyncio_task_scheduler.py](./asyncio_task_scheduler.py) | `AsyncioTaskScheduler`: `TaskScheduler` running the workspace on the server event loop. |
| [event_hub.py](./event_hub.py) | `EventHub`: sends changed topics (merged when they arrive in quick succession) and notices to every connected browser. |
| [image_routes.py](./image_routes.py) | `ImageRoutes`: opening, closing, showing and uploading images, image previews and server folder listings. |
| [class_routes.py](./class_routes.py) | `ClassRoutes`: editing classes, phrases and reference images, and the saved class sets. |
| [detection_routes.py](./detection_routes.py) | `DetectionRoutes`: state, model choice, detection runs, stored profiles, comparison, reviewing, class minimums and CSV of listed detections. |
| [export_routes.py](./export_routes.py) | `ExportRoutes`: export plan, export on the server and ZIP download of the files the last export wrote. |
| [payload_builder.py](./payload_builder.py) | `PayloadBuilder`: JSON documents describing the workspace to the browser. |
| [json_value.py](./json_value.py) | `JsonValue` and `JsonObject` type aliases of JSON payloads. |
| [profile_key.py](./profile_key.py) | `ProfileKey`: text naming a detector profile in the browser. |
| [directory_browser.py](./directory_browser.py) | `DirectoryBrowser`: folders and image files of a server directory, hidden entries left out. |
| [image_preview_cache.py](./image_preview_cache.py) | `ImagePreviewCache`: upright images encoded as JPEG for the browser, downscaled when large and cached in memory. |
| [image_preview.py](./image_preview.py) | `ImagePreview`: encoded image bytes with their MIME type. |
| [image_info.py](./image_info.py) | `ImageInfo`: version and upright size of an image file, read without decoding its pixels. |
| [reference_draft_store.py](./reference_draft_store.py) | `ReferenceDraftStore`: reference images opened for boxing, kept until added to a class or pushed out. |
| [reference_draft.py](./reference_draft.py) | `ReferenceDraft`: reference image waiting for the user to box its examples. |
| [schema/](./schema/README.md) | Pydantic request bodies of the API. |

## Examples

```python
from pathlib import Path

from ovd_gui.web import WebLauncher

WebLauncher("127.0.0.1", 8000, is_browser_opened=True).run([Path("images/")])
```

```bash
ovd-gui --no-browser --port 8000
ssh -L 8000:localhost:8000 host  # then open http://localhost:8000 on the local machine
```
