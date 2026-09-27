# storage

## Overview

Named class sets: classes with their phrases and every image prompt, saved so that loading a set restores exactly
what was queried. A set is one self-contained ZIP archive (`.ovdset`) that stores the pixels of each reference image
losslessly, so it does not depend on where the original image files were and can be copied to another machine.
Reference images are identified by their name and pixel digest, never by a file path.

```text
ovd_gui_data/
└── classes/<name>.ovdset
    ├── manifest.json        # format, version, classes with phrases, reference images, reference boxes
    └── images/<sha256>.png  # lossless pixels of each reference image, checked against the digest on load
```

## Components

| Component | Description |
| --------- | ----------- |
| [class_set.py](./class_set.py) | `ClassSet`: classes, their reference boxes and the pixels of the boxed images, captured from a `ReferenceBoard`. |
| [class_set_archive.py](./class_set_archive.py) | `ClassSetArchive`: reads and writes one `ClassSet` as a `.ovdset` ZIP archive, or only its summary, rejecting foreign, malformed or tampered files. |
| [class_set_summary.py](./class_set_summary.py) | `ClassSetSummary`: class names, phrase and image counts read from the manifest alone. |
| [class_set_entry.py](./class_set_entry.py) | `ClassSetEntry`: listed set with its save time and summary, or no summary when the file cannot be read. |
| [class_set_store.py](./class_set_store.py) | `ClassSetStore`: named class sets in the `classes` directory of the data directory: listed with summaries, read, written, deleted, renamed, imported and exported. |

## Examples

```python
from ovd_gui.detection import ReferenceBoard
from ovd_gui.storage import ClassSet, ClassSetStore
from ovd_gui.vocabulary import ClassDefinition

board = ReferenceBoard()
store = ClassSetStore.in_working_directory()
store.write_class_set("vehicles", ClassSet.of((ClassDefinition.parse("car: car, suv"),), board))

class_set = store.read_class_set("vehicles")
board.replace(class_set.reference_boxes, class_set.reference_pixels)

for entry in store.entries:
    print(entry.name, entry.summary.description if entry.summary else "unreadable")
store.rename_class_set("vehicles", "traffic")
store.delete_class_set("traffic")
```
