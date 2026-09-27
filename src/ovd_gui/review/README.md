# review

## Overview

Qt-independent rules deciding which stored detections are kept after detection: the minimum confidence of each
class, set on top of the detector's own threshold so that it can be tuned without detecting again. Rejections of
single detections are kept by `DetectionCatalog`.

## Components

| Component | Description |
| --------- | ----------- |
| [class_thresholds.py](./class_thresholds.py) | `ClassThresholds`: default minimum confidence and per-class overrides, compared by value. |

## Examples

```python
from ovd_gui.review import ClassThresholds

thresholds = ClassThresholds(0.2).with_class_minimum("car", 0.45)
thresholds.accepts("car", 0.4)
```
