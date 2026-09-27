# OVD-GUI

## Overview

Desktop GUI (PySide6) for [OpenVocabularyDetector](https://github.com/ry-yoshida-dev/OpenVocabularyDetector). Open
images, type the classes to detect, pick a model, and see boxes and a detection table.

- **Models are switched by preset**: every YAML preset shipped in `open_vocabulary_detector/config/` is listed by
  backend (Grounding DINO, OWL-ViT, YOLO-World, YOLOE) and built into `DetectorSettings` with
  [DataclassInitializer](https://github.com/ry-yoshida-dev/DataclassInitializer).
- **Overrides without editing YAML**: device, float16, confidence and NMS thresholds can be changed per run.
- **Loaded model is reused**: changing only thresholds does not reload the model; changing the preset, device or
  precision does.
- **Classes are queried by several phrases**: `car: car, suv, taxi` detects cars with any of the phrases and reports
  them as `car`; the detection table shows which phrase matched. A class written without a colon is prompted by its
  name.
- **Image prompts**: with OWL-ViT or YOLOE, example images can be added to a class, separately from the images to
  analyze; examples are boxed in a dialog, or the whole image is used. Each reference image becomes one more prompt
  of the class, next to its phrases. With a model that takes phrases only, classes that have reference images but no
  phrase are listed in a confirmation and, once accepted, left out of the run.
- **Open images are detected in the background**: every open image without an up-to-date result for the current
  model is detected one by one in the background, the shown image first, without blocking the window. Your own
  actions come first: `Detect`, `Detect All` and export start right after the image being inferred, a newly shown
  image is detected before the others, and an image opened during `Detect All` is detected next. A failed
  background detection pauses the others until you open, show or detect images or edit the classes.
- **Search across images**: `Detect All` detects every open image; the detection table lists the current image or
  all images with the image name, filters any column from the `Filter` button below it or by right-clicking its header (checked values for image,
  class and query; bounds for confidence and box corners) and sorts by any column.
  Each image keeps its latest result, so revisiting it shows its boxes without detecting again.
- **Compare models without detecting again**: results are kept per model and options (device, precision,
  thresholds). Detecting with another preset adds a row to the `Models` table above the detection table instead of
  replacing earlier results; selecting a row there switches the boxes and the detection table to that model's
  results.
- **Edit classes without losing results**: adding, removing or rewording a class keeps every result. Images detected
  with other classes are marked with a warning icon in the detection table (its tool tip names the added, removed or
  edited classes) and counted under `Outdated` in the `Models` table; they are detected again in the
  background, the shown image first, and `Update Outdated` detects them all at once.
- **Results are remembered**: results of every model, with the rejected detections, are saved to
  `ovd_gui_data/results.ovdresults` shortly after each change and restored at the next start for image files that
  have not changed; opening the same images again shows them without detecting. The class minimums are kept in
  `ovd_gui_data/class_thresholds.json`.
- **Open images are remembered**: the open images and the shown one are kept in `ovd_gui_data/session.json` and
  opened again at the next start without command-line arguments; files that no longer exist are skipped.
- **Image list status**: each open image shows whether it is detected, outdated, failed or not analyzed with the
  shown model, and how many of its detections are kept.
- **Review detections**: unchecking `Keep` in the detection table rejects a detection (Space toggles the selected
  one; the right-click menu keeps or rejects every listed one, e.g. after filtering low confidences). The image draws
  only the detections the table lists, so its column filters also filter the boxes, and rejected boxes are dashed.
- **Minimum confidence per class**: set in the statistics window on top of the detector threshold; detections below
  it are hidden from the table and the image and left out of exports, without detecting again.
- **Statistics and model comparison**: `Statistics…` counts the detections of each class over the open images with a
  confidence histogram, and compares the shown model with another stored one class by class (detections paired by
  box overlap); the compared model's boxes are drawn dotted over the image.
- **Export to annotation formats**: the stored results of the shown model are saved as MS COCO, YOLO, Pascal VOC,
  LabelMe or Create ML with [ObjectDetectionFormat](https://github.com/ry-yoshida-dev/ObjectDetectionFormat),
  leaving out rejected detections and those below the class minimums, optionally also those hidden by the table
  filters or below an export minimum. Open images without an up-to-date result are detected first. Optionally, a
  copy of every exported image with its exported boxes drawn is saved in `annotated_images/` of the output directory.
- **Detection table as CSV**: `Save CSV…` below the detection table (or its right-click menu) saves the listed
  detections in display order with image path, class, prompt, confidence, box corners and whether each is kept.
- **Classes are remembered**: the classes and their phrases are kept in `ovd_gui_data/` under the working directory
  and restored at the next start.
- **Class sets keep image prompts**: a named class set is saved as one self-contained archive,
  `ovd_gui_data/classes/<name>.ovdset`, holding the classes, their phrases, the reference boxes and the pixels of
  every reference image, so loading it restores the image prompts even when the original image files are moved or
  gone, and the file can be copied to another machine. Plain class lists (`name` or `name: phrase, phrase` per line,
  compatible with YOLO `classes.txt` and Darknet `.names`) can still be loaded with `From File…`.
- **GUI stays responsive**: loading and inference run on a worker thread.

Weights are downloaded on first use; Ultralytics weights are saved to the current
working directory. Nothing is written to OS-level settings; application data stays in `ovd_gui_data/`.

## Installation

```bash
pip install -e ".[dev]"
```

For local development against sibling checkouts:

```bash
pip install -e ../OpenVocabularyDetector -e ../DataclassInitializer -e ../ObjectDetectionFormat -e ".[dev]"
```

## Development

```bash
uv sync --extra dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src tests
uv run basedpyright
QT_QPA_PLATFORM=offscreen uv run pytest
```

The same checks run on every push and pull request in [GitHub Actions](.github/workflows/ci.yml). Git dependencies
are pinned to commits in `pyproject.toml`; update the commit there and run `uv lock` to upgrade one.

## Examples

```bash
ovd-gui
ovd-gui path/to/images/ photo.jpg  # without arguments, the images open at the last close are opened again
python -m ovd_gui
```

| Action | How |
| ------ | --- |
| Open images | Drop files or folders anywhere on the window, `Open Images…` / `Open Folder…`, or command-line arguments |
| Add a class or phrase | `+ Text` above the class tree adds a row next to the selection at the same level: a class after a selected class, a phrase after a selected phrase, a class at the end when nothing is selected (double-clicking the empty area also adds a class). Type the name and press Enter; Escape cancels. `suv, taxi` adds two phrases, and `car: car, suv` names the phrases of a new class |
| Move a prompt | Drag a phrase onto another class or between its phrases to move it there; drop it between classes or below the rows to make it a class of its own. Reference images can be dragged to another class |
| Edit or remove | Double-click a class or phrase to edit it; the trash button or Delete removes the selected classes, phrases or reference images; the same actions are in the right-click menu |
| Save / load classes | The `Set` drop-down above the class tree lists the class sets saved in `ovd_gui_data/classes/`; choosing one loads it (asking first whenever unsaved classes would be discarded; `Edited` marks edits since the set was loaded or saved). `Save…` next to it asks only for a set name and saves the classes with their phrases and reference images. The three-dot menu › `Open File…` takes an `.ovdset` archive or a class list text file from elsewhere |
| Manage class sets | Three-dot menu › `Class Sets…` opens the library: search sets and classes, preview the classes and image prompts of a set, `Load` (or double-click) to replace the current classes, rename in place (F2), delete with confirmation (Delete or the trash button), `Import…` / `Export…` `.ovdset` files |
| Add an image prompt | Select a class, press `+ Image`, drop example images or folders onto the window (or use `Open Images…` / `Open Folder…`), then drag boxes around the examples or press `Use Whole Image`; each image appears under the class as one prompt |
| Detect | Open an image (every image is detected in the background when it has no result yet), or `Detect` / Ctrl+Enter to detect it again |
| Detect every image | `Detect All` or Ctrl+Shift+Enter (cancellable); every image fills in the table as it is detected |
| Find images showing a class | `Filter` › `Class` below the table (or right-click the `Class` header) and check the classes; click a column header to sort, e.g. by `Confidence` |
| Jump to a detection | Select its row; its image opens and the box is highlighted |
| Compare models | Detect with one preset, change the preset (or thresholds) and detect again; select a row of the `Models` table to switch between their results |
| Refresh after editing classes | `Update Outdated` below the table detects again only the images marked outdated |
| Forget results | `Remove` above the `Models` table (or Delete) forgets the selected model; `Clear Results` below the table forgets every model |
| Fold panels | Click a sidebar section header |
| Zoom | Mouse wheel; double-click fits the image again |
| Browse images | ◀ / ▶ in the toolbar, or Left / Right (Page Up / Page Down) on the image or the image list |
| Close images | Select them in the image list and press Delete or use the right-click menu; their results are kept |
| Keep or reject detections | Check or uncheck `Keep` in the detection table, press Space on a row, or right-click › `Keep All Listed` / `Reject All Listed` |
| Change how boxes are drawn | `View` in the toolbar: labels, confidences, rejected boxes, compared model, line width, fill |
| Set class minimums | `Statistics…` (Ctrl+I): the default minimum and the `Min. Confidence` column; the histogram marks the minimum of the selected class |
| Compare with another model | `Statistics…` › `Compare With`: per-class counts, and the compared boxes drawn dotted on the image |
| Export results | `Export…` or Ctrl+E; choose the format, output directory, exported detections and minimum confidence, and whether images with boxes drawn are saved too; images without an up-to-date result are detected first (cancellable) |
| Save the table | `Save CSV…` below the detection table, or right-click › `Save Listed as CSV…`; only the listed rows are saved, in display order |
