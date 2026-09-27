# statistics

## Overview

Non-modal statistics window of the shown model over the open images: detections per class with their rejected,
below-minimum and kept counts and mean and median confidence, a confidence histogram of the selected class (or of
every class), the minimum confidence of each class and the default one, and a class-by-class comparison with another
stored model.

## Components

| Component | Description |
| --------- | ----------- |
| [statistics_window.py](./statistics_window.py) | `StatisticsWindow`: class table with editable minimums, histogram and model comparison; reports threshold and comparison changes. |
| [confidence_histogram_view.py](./confidence_histogram_view.py) | `ConfidenceHistogramView`: bar chart of a `ConfidenceHistogram` with the minimum marked and lower bars faded. |
| [minimum_spin_box.py](./minimum_spin_box.py) | `MinimumSpinBox`: optional minimum confidence, `Default` meaning the class uses the default minimum. |
| [statistics_column.py](./statistics_column.py) | `StatisticsColumn`: columns of the class table. |
| [comparison_column.py](./comparison_column.py) | `ComparisonColumn`: columns of the comparison table. |
