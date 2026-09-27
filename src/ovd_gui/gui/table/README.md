# table

## Overview

Detection table on the right of the window: every open image with its detections, filtered, sorted, and selectable
to jump to their image. Images without detections say whether they are not analyzed yet or have no detections, and
the rows of the shown image are highlighted.

## Components

| Component | Description |
| --------- | ----------- |
| [result_panel.py](./result_panel.py) | `ResultPanel`: table with class, image name and confidence filters in one row; selecting a row reports its detection or image. |
| [result_row_model.py](./result_row_model.py) | `ResultRowModel`: rows per open image with image, class, matched query, confidence and box columns; highlights the current image. |
| [result_filter_proxy_model.py](./result_filter_proxy_model.py) | `ResultFilterProxyModel`: sorted view listing the rows accepted by a `DetectionFilter`. |
| [result_row.py](./result_row.py) | `ResultRow`: a detection or an image status row. |
| [image_status_row.py](./image_status_row.py) | `ImageStatusRow`: row of an open image without any detection to list. |
| [analysis_state.py](./analysis_state.py) | `AnalysisState`: not analyzed or detected without result. |
| [class_filter_button.py](./class_filter_button.py) | `ClassFilterButton`: funnel button whose menu checks the listed classes. |
| [funnel_icon.py](./funnel_icon.py) | `FunnelIcon`: funnel icon, filled while a filter is in effect. |
| [result_column.py](./result_column.py) | `ResultColumn`: columns of the detection table. |
