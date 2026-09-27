# table

## Overview

Right side of the window: the model table listing every detector profile with stored results, and the detection
table listing every open image with the detections of the selected profile, filtered, sorted, and selectable to jump
to their image. Images without detections say whether they are not analyzed yet or have no detections, and
the rows of the shown image are highlighted. Every column of the detection table is filtered from the funnel in its
header: text columns by checking values, numeric columns (confidence, box corners) by lower and upper bounds.

## Components

| Component | Description |
| --------- | ----------- |
| [profile_panel.py](./profile_panel.py) | `ProfilePanel`: model table with options and counts per profile; selecting a row shows its results, Remove forgets them. |
| [profile_column.py](./profile_column.py) | `ProfileColumn`: columns of the model table. |
| [result_panel.py](./result_panel.py) | `ResultPanel`: detection table with a filter per column and a Clear Filters button; selecting a row reports its detection or image. |
| [result_row_model.py](./result_row_model.py) | `ResultRowModel`: rows per open image with image, class, matched query, confidence and box columns; highlights the current image. |
| [result_filter_proxy_model.py](./result_filter_proxy_model.py) | `ResultFilterProxyModel`: sorted view listing the rows passing a `TableFilter`; supplies the header funnels and the values to filter by. |
| [result_row.py](./result_row.py) | `ResultRow`: a detection or an image status row. |
| [image_status_row.py](./image_status_row.py) | `ImageStatusRow`: row of an open image without any detection to list. |
| [analysis_state.py](./analysis_state.py) | `AnalysisState`: not analyzed or detected without result. |
| [filter_header_view.py](./filter_header_view.py) | `FilterHeaderView`: header asking for a column filter on a funnel click or right-click, sorting otherwise. |
| [column_filter_popup.py](./column_filter_popup.py) | `ColumnFilterPopup`: popup applying or clearing the condition of one column. |
| [value_checklist.py](./value_checklist.py) | `ValueChecklist`: searchable checklist of the values of a text column. |
| [range_editor.py](./range_editor.py) | `RangeEditor`: optional lower and upper bounds of a numeric column. |
| [table_filter.py](./table_filter.py) | `TableFilter`: condition of each filtered column. |
| [column_condition.py](./column_condition.py) | `ColumnCondition`: a value or range condition. |
| [value_condition.py](./value_condition.py) | `ValueCondition`: checked values of a text column. |
| [range_condition.py](./range_condition.py) | `RangeCondition`: bounds of a numeric column. |
| [number_span.py](./number_span.py) | `NumberSpan`: smallest and largest value of a numeric column. |
| [funnel_icon.py](./funnel_icon.py) | `FunnelIcon`: funnel icon, filled while a filter is in effect. |
| [result_column.py](./result_column.py) | `ResultColumn`: columns of the detection table. |
