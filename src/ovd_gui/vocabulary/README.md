# vocabulary

## Overview

The classes to detect and their persistence. A class is an output label and the phrases the model reads for it,
written `car: car, suv, taxi`; a plain `car` is queried by its own name. `ClassVocabulary` keeps class names and
phrases unique regardless of case, since a phrase can report only one class.

The class list lives in a data directory (`ovd_gui_data/` under the working directory): the list of the last run is
restored at start, and class lists are saved to or loaded from plain-text files with one class per line. Classes
queried by their name only are written as plain names, so such files stay compatible with YOLO `classes.txt` and
Darknet `.names`. Named class sets are addressed by name only.

```text
ovd_gui_data/
├── last_classes.txt   # class list of the last run, restored at start
└── classes/<name>.txt # named class sets from Save... / Load
```

## Components

| Component | Description |
| --------- | ----------- |
| [class_definition.py](./class_definition.py) | `ClassDefinition`: class name and phrases, parsed from and written as `name: phrase, phrase`. |
| [class_vocabulary.py](./class_vocabulary.py) | `ClassVocabulary`: ordered classes with unique names and phrases, edited by class id. |
| [class_list_file.py](./class_list_file.py) | `ClassListFile`: reads and writes a one-class-per-line text file. |
| [class_list_store.py](./class_list_store.py) | `ClassListStore`: data directory remembering the last class list and holding named class sets. |

## Examples

```python
from ovd_gui.vocabulary import ClassDefinition, ClassListStore, ClassVocabulary

vocabulary = ClassVocabulary()
vocabulary.add(ClassDefinition.parse("car: car, suv, taxi"))
vocabulary.add(ClassDefinition.named("person"))

store = ClassListStore.in_working_directory()
store.save(vocabulary.classes)
remembered = store.load()

store.write_class_set("traffic", vocabulary.classes)
store.read_class_set("traffic")
```
