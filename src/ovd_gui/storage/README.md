# storage

## Overview

Application data kept in `ovd_gui_data/` under the working directory: named class sets with their image prompts,
the detection results of every model with the rejected detections, the minimum confidence of each class, and the
images open when the window last closed.

A class set is one self-contained ZIP archive (`.ovdset`) that stores the pixels of each reference image losslessly,
so it does not depend on where the original image files were and can be copied to another machine. Reference images
are identified by their name and pixel digest, never by a file path.

The results archive (`results.ovdresults`) stores, per detector profile, the boxes, confidences, matched queries and
rejected detections of every image, with the prompts they were detected with (including the pixels of image
prompts). Each image records the modification time and size of its file, so results of files changed or removed since
are dropped when the archive is read.

```text
ovd_gui_data/
├── classes/<name>.ovdset
│   ├── manifest.json        # format, version, classes with phrases, reference images, reference boxes
│   └── images/<sha256>.png  # lossless pixels of each reference image, checked against the digest on load
├── results.ovdresults
│   ├── manifest.json        # profiles, images with boxes and rejections, prompts with labels and signatures
│   └── images/<sha256>.png  # pixels of the reference images used by visual queries
├── class_thresholds.json    # default and per-class minimum confidence
└── session.json             # open image files and the shown one
```

## Components

| Component | Description |
| --------- | ----------- |
| [class_set.py](./class_set.py) | `ClassSet`: classes, their reference boxes and the pixels of the boxed images, captured from a `ReferenceBoard`. |
| [class_set_archive.py](./class_set_archive.py) | `ClassSetArchive`: reads and writes one `ClassSet` as a `.ovdset` ZIP archive, or only its summary, rejecting foreign, malformed or tampered files. |
| [class_set_summary.py](./class_set_summary.py) | `ClassSetSummary`: class names, phrase and image counts read from the manifest alone. |
| [class_set_entry.py](./class_set_entry.py) | `ClassSetEntry`: listed set with its save time and summary, or no summary when the file cannot be read. |
| [class_set_store.py](./class_set_store.py) | `ClassSetStore`: named class sets in the `classes` directory of the data directory: listed with summaries, read, written, deleted, renamed, imported and exported. |
| [result_archive.py](./result_archive.py) | `ResultArchive`: reads and writes every stored result of a `ResultLibrary` as one ZIP archive. |
| [result_manifest_writer.py](./result_manifest_writer.py) | `ResultManifestWriter`: converts a `ResultLibrary` into the archive manifest, collecting reference image pixels. |
| [result_manifest_reader.py](./result_manifest_reader.py) | `ResultManifestReader`: rebuilds a `ResultLibrary` from the manifest, dropping results of changed image files. |
| [result_store.py](./result_store.py) | `ResultStore`: the results archive of the data directory, empty when nothing is saved. |
| [class_threshold_store.py](./class_threshold_store.py) | `ClassThresholdStore`: minimum confidence per class remembered as JSON. |
| [session.py](./session.py) | `Session`: open image files in list order and the shown one. |
| [session_store.py](./session_store.py) | `SessionStore`: the open images remembered as JSON, an empty session when nothing or nothing readable is stored. |
| [json_fields.py](./json_fields.py) | `JsonFields`: typed access to parsed JSON values with errors naming the field. |

## Examples

```python
from ovd_gui.detection import ReferenceBoard
from ovd_gui.storage import ClassSet, ClassSetStore, ResultStore
from ovd_gui.vocabulary import ClassDefinition

board = ReferenceBoard()
store = ClassSetStore.in_working_directory()
store.write_class_set("vehicles", ClassSet.of((ClassDefinition.parse("car: car, suv"),), board))

class_set = store.read_class_set("vehicles")
board.replace(class_set.reference_boxes, class_set.reference_pixels)

result_store = ResultStore.in_working_directory()
result_store.save(library)
library = result_store.load()
```
