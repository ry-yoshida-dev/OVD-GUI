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
- **The shown image is always detected**: opening an image detects it in the background with the current model
  when it has no result yet, without blocking the window. Your own actions come first: `Detect`, `Detect All` and
  export start right after the image being inferred, switching images quickly detects only the last one, and an
  image opened during `Detect All` is detected next.
- **Search across images**: `Detect All` detects every open image; the detection table lists the current image or
  all images with the image name, filters any column from the funnel in its header (checked values for image,
  class and query; bounds for confidence and box corners) and sorts by any column.
  Each image keeps its latest result, so revisiting it shows its boxes without detecting again.
- **Compare models without detecting again**: results are kept per model and options (device, precision,
  thresholds). Detecting with another preset adds a row to the `Models` table above the detection table instead of
  replacing earlier results; selecting a row there switches the boxes and the detection table to that model's
  results. Results are kept in memory for the session only.
- **Export to annotation formats**: every open image is detected with the current model and classes, and the
  results are saved as MS COCO, YOLO, Pascal VOC, LabelMe or Create ML with [ObjectDetectionFormat](https://github.com/ry-yoshida-dev/ObjectDetectionFormat).
- **Classes are remembered**: the classes and their phrases are kept in `ovd_gui_data/` under the working directory
  and restored at the next start.
- **Class sets keep image prompts**: a named class set is saved as one self-contained archive,
  `ovd_gui_data/classes/<name>.ovdset`, holding the classes, their phrases, the reference boxes and the pixels of
  every reference image, so loading it restores the image prompts even when the original image files are moved or
  gone, and the file can be copied to another machine. Plain class lists (`name` or `name: phrase, phrase` per line,
  compatible with YOLO `classes.txt` and Darknet `.names`) can still be loaded with `From File...`.
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

## Examples

```bash
ovd-gui
ovd-gui path/to/images/ photo.jpg
python -m ovd_gui
```

| Action | How |
| ------ | --- |
| Open images | Drop files or folders anywhere on the window, `Open Images...` / `Open Folder...`, or command-line arguments |
| Add a class or phrase | `+ Text` above the class tree adds a row next to the selection at the same level: a class after a selected class, a phrase after a selected phrase, a class at the end when nothing is selected (double-clicking the empty area also adds a class). Type the name and press Enter; Escape cancels. `suv, taxi` adds two phrases, and `car: car, suv` names the phrases of a new class |
| Move a prompt | Drag a phrase onto another class or between its phrases to move it there; drop it between classes or below the rows to make it a class of its own. Reference images can be dragged to another class |
| Edit or remove | Double-click a class or phrase to edit it; the trash button or Delete removes the selected classes, phrases or reference images; the same actions are in the right-click menu |
| Save / load classes | The `Set` drop-down above the class tree lists the class sets saved in `ovd_gui_data/classes/`; choosing one loads it (asking first when the current classes were edited, which `Edited` marks). `Save...` next to it asks only for a set name and saves the classes with their phrases and reference images. `⋯` › `Load From File...` takes an `.ovdset` archive or a class list text file from elsewhere |
| Manage class sets | `⋯` › `Class Sets...` opens the library: search sets and classes, preview the classes and image prompts of a set, `Load` (or double-click) to replace the current classes, rename in place (F2), delete with confirmation (Delete or the trash button), `Import...` / `Export...` `.ovdset` files |
| Add an image prompt | Select a class, press `+ Image`, drop example images or folders onto the window (or use `Open Images…` / `Open Folder…`), then drag boxes around the examples or press `Use Whole Image`; each image appears under the class as one prompt |
| Detect | Open an image (detected in the background when it has no result yet), or `Detect` / Ctrl+Enter to detect it again |
| Detect every image | `Detect All` or Ctrl+Shift+Enter (cancellable); every image fills in the table as it is detected |
| Find images showing a class | Check the classes in the funnel menu above the table; click a column header to sort, e.g. by `Confidence` |
| Jump to a detection | Select its row; its image opens and the box is highlighted |
| Compare models | Detect with one preset, change the preset (or thresholds) and detect again; select a row of the `Models` table to switch between their results |
| Forget results | `Remove` above the `Models` table (or Delete) forgets the selected model; `Clear Results` below the table forgets every model |
| Fold panels | Click a sidebar section header |
| Zoom | Mouse wheel; double-click fits the image again |
| Export results | `Export...` or Ctrl+E; choose the format and output directory, then every open image is detected and saved (cancellable) |
