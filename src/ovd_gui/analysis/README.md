# analysis

## Overview

Qt-independent statistics over stored results: per-class counts and confidences of one detector profile over the
open images, taking rejected detections and the class minimums into account, and a class-by-class comparison of two
profiles whose detections are paired one to one by box overlap.

## Components

| Component | Description |
| --------- | ----------- |
| [result_statistics.py](./result_statistics.py) | `ResultStatistics`: per-class statistics of one profile over some images, current classes first. |
| [class_statistics.py](./class_statistics.py) | `ClassStatistics`: image, detection, rejected, below-minimum and kept counts of one class with its confidences, mean, median and histogram. |
| [confidence_histogram.py](./confidence_histogram.py) | `ConfidenceHistogram`: detections per equal-width confidence bin over `[0, 1]`. |
| [profile_comparison.py](./profile_comparison.py) | `ProfileComparison`: detections of two profiles per class on the images both detected, with the matched counts. |
| [class_comparison.py](./class_comparison.py) | `ClassComparison`: shown, compared and matched counts of one class, and those only one model found. |
| [box_matcher.py](./box_matcher.py) | `BoxMatcher`: greedy one-to-one pairing of two box sets by intersection over union. |

## Examples

```python
from ovd_gui.analysis import ProfileComparison, ResultStatistics
from ovd_gui.review import ClassThresholds

statistics = ResultStatistics.of(catalog, image_paths, ("person", "car"), ClassThresholds(0.0, {"car": 0.4}))
for entry in statistics.classes:
    print(entry.class_name, entry.kept_count, entry.mean_confidence)

comparison = ProfileComparison.between(owl_vit_catalog, grounding_dino_catalog, image_paths, ("person", "car"))
```
