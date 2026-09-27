# analysis

## Overview

Tests of `ovd_gui.analysis`.

## Components

| Component | Description |
| --------- | ----------- |
| [test_confidence_histogram.py](./test_confidence_histogram.py) | Binning of confidences over `[0, 1]`. |
| [test_box_matcher.py](./test_box_matcher.py) | One-to-one pairing of boxes by overlap. |
| [test_result_statistics.py](./test_result_statistics.py) | Per-class statistics with rejected and below-minimum detections, and comparison of two profiles. |
