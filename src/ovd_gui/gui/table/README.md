# table

## Overview

Right side of the window: the model table listing every detector profile with stored results, and the detection
table listing every open image with the detections of the selected profile, filtered, sorted, and selectable to jump
to their image. Images without detections say whether they are not analyzed yet or have no detections, and
the rows of the shown image are highlighted. Images detected with other classes than the current ones are marked
with a warning icon and counted in the model table; `Update Outdated` asks to detect them again. Every column of the
detection table is filtered from the single `Filter` button below it, or by right-clicking its header: text columns by checking values, numeric columns
(confidence, box corners) by lower and upper bounds. Only filtered columns show a funnel in their header. Columns of both tables can be resized by dragging their edges;
they are as wide as their cells until the user resizes one.

The `Keep` check box of a detection rejects it for export when unchecked; Space toggles the selected detection and
the right-click menu keeps or rejects every listed detection. Detections below the minimum confidence of their class
are not listed.

## Components

| Component | Description |
| --------- | ----------- |
| [profile_panel.py](./profile_panel.py) | `ProfilePanel`: model table with backend, model, device, precision, thresholds, image, outdated image and detection counts per profile; selecting a row shows its results, Remove forgets them. |
| [profile_column.py](./profile_column.py) | `ProfileColumn`: columns of the model table with their headers and cell texts. |
| [result_panel.py](./result_panel.py) | `ResultPanel`: detection table with a filter per column, class minimums, keeping and rejecting detections, saving the listed detections as CSV, Clear Filters and Update Outdated buttons; selecting a row reports its detection or image, and new results or filters never move the selection to another image. |
| [result_row_model.py](./result_row_model.py) | `ResultRowModel`: rows per open image with keep check box, image, class, matched query, confidence and box columns; highlights the current image, marks outdated images and greys out rejected detections. |
| [result_filter_proxy_model.py](./result_filter_proxy_model.py) | `ResultFilterProxyModel`: sorted view listing the rows passing a `TableFilter` and the class minimums; supplies the funnels of filtered headers and the values to filter by. |
| [result_row.py](./result_row.py) | `ResultRow`: a detection or an image status row. |
| [image_status_row.py](./image_status_row.py) | `ImageStatusRow`: row of an open image without any detection to list. |
| [column_auto_fit.py](./column_auto_fit.py) | `ColumnAutoFit`: resizable columns given a default width per column until the user resizes one. |
| [analysis_state.py](./analysis_state.py) | `AnalysisState`: not analyzed or detected without result. |
| [filter_header_view.py](./filter_header_view.py) | `FilterHeaderView`: header asking for a column filter on a right-click or a click on the funnel of a filtered column, sorting otherwise. |
| [column_filter_popup.py](./column_filter_popup.py) | `ColumnFilterPopup`: popup applying or clearing the condition of one column. |
| [value_checklist.py](./value_checklist.py) | `ValueChecklist`: searchable checklist of the values of a text column. |
| [range_editor.py](./range_editor.py) | `RangeEditor`: optional lower and upper bounds of a numeric column. |
| [table_filter.py](./table_filter.py) | `TableFilter`: condition of each filtered column. |
| [column_condition.py](./column_condition.py) | `ColumnCondition`: a value or range condition. |
| [value_condition.py](./value_condition.py) | `ValueCondition`: checked values of a text column. |
| [range_condition.py](./range_condition.py) | `RangeCondition`: bounds of a numeric column. |
| [number_span.py](./number_span.py) | `NumberSpan`: smallest and largest value of a numeric column. |
| [funnel_icon.py](./funnel_icon.py) | `FunnelIcon`: funnel icon, filled while a filter is in effect. |
| [outdated_icon.py](./outdated_icon.py) | `OutdatedIcon`: warning triangle marking results detected with other classes. |
| [result_column.py](./result_column.py) | `ResultColumn`: columns of the detection table. |
