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
  them as `car`; the detection table shows which phrase matched. A class written without a colon is queried by its
  name.
- **Image prompts**: with OWL-ViT or YOLOE, example images can be added to a class, separately from the images to
  analyze; examples are boxed in a dialog, or the whole image is used. Each reference image becomes one more query
  of the class, next to its phrases.
- **Search across images**: `Detect All` detects every open image; the detection table lists the current image or
  all images with the image name, and filters by class, image name and minimum confidence and sorts by any column.
  Each image keeps its latest result, so revisiting it shows its boxes without detecting again.
- **Export to annotation formats**: every open image is detected with the current model and classes, and the
  results are saved as MS COCO, YOLO, Pascal VOC, LabelMe or Create ML with [ObjectDetectionFormat](https://github.com/ry-yoshida-dev/ObjectDetectionFormat).
- **Classes are remembered**: the classes and their phrases are kept in `ovd_gui_data/` under the working directory
  and restored at the next start; named class sets are saved as `ovd_gui_data/classes/<name>.txt` with one class
  per line, `name` or `name: phrase, phrase` (plain lists stay compatible with YOLO `classes.txt` and Darknet
  `.names`). Reference images are kept for the session only.
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
| Edit classes | Type `cat, dog` or `car: car, suv, taxi` below the class tree and press Enter; double-click a class or phrase to edit it; Delete removes the selected classes, phrases or reference images |
| Add phrases | Select a class and press `Add Phrases...`, or type `car: van` to extend an existing class |
| Save / load classes | `Save...` below the class tree asks only for a set name; `Load` lists the saved sets (or `From File...`) and replaces the current classes |
| Add an image prompt | Select a class, press `Add Images...`, pick example images, then drag boxes around the examples or press `Use Whole Image`; each image appears under the class as one query |
| Detect | `Detect`, Enter in the empty class field, or Ctrl+Enter |
| Detect every image | `Detect All` or Ctrl+Shift+Enter (cancellable); the table switches to `All images` |
| Find images showing a class | Choose `All images` and the class above the table; click a column header to sort, e.g. by `Confidence` |
| Jump to a detection | Select its row; its image opens and the box is highlighted |
| Forget results | `Clear Results` below the table |
| Fold panels | Click a sidebar section header |
| Zoom | Mouse wheel; double-click fits the image again |
| Export results | `Export...` or Ctrl+E; choose the format and output directory, then every open image is detected and saved (cancellable) |
