# table

## Overview

Detection table on the right of the window: detections of the current or every detected image, filtered, sorted,
and selectable to jump to their image.

## Components

| Component | Description |
| --------- | ----------- |
| [result_panel.py](./result_panel.py) | `ResultPanel`: table with scope, class, image name and confidence filters; selecting a row reports its detection. |
| [detection_record_model.py](./detection_record_model.py) | `DetectionRecordModel`: detection records as rows with image, class, matched query, confidence and box columns. |
| [detection_filter_proxy_model.py](./detection_filter_proxy_model.py) | `DetectionFilterProxyModel`: sorted view listing the rows accepted by a `DetectionFilter`. |
| [result_column.py](./result_column.py) | `ResultColumn`: columns of the detection table. |
| [result_scope.py](./result_scope.py) | `ResultScope`: whether the table lists the current image or every image. |
