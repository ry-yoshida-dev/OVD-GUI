# viewer

## Overview

Zoomable image view drawing detection and reference boxes over the image, also used to draw and adjust reference
rectangles. Only the detections listed in the detection table are drawn: kept ones solid, rejected ones dashed and
faded, and those of a compared model dotted; the View menu chooses labels, confidences, rejected boxes, the compared
model, line width and fill.

## Components

| Component | Description |
| --------- | ----------- |
| [image_canvas.py](./image_canvas.py) | `ImageCanvas`: zoomable view of a PIL image with detection and reference boxes; draws rectangles, and moves and resizes reference boxes, in drawing mode. |
| [detection_overlay.py](./detection_overlay.py) | `DetectionOverlay`: result of the shown image with its listed and rejected detections and the compared model's result. |
| [display_options.py](./display_options.py) | `DisplayOptions`: labels, confidences, rejected and compared boxes, line width and fill. |
| [display_menu.py](./display_menu.py) | `DisplayMenu`: View menu editing the `DisplayOptions`. |
| [box_style.py](./box_style.py) | `BoxStyle`: kept, rejected or compared box, deciding its outline and opacity. |
| [box_grab.py](./box_grab.py) | `BoxGrab`: reference box held by the mouse and the fixed point of the drag. |
| [box_grab_kind.py](./box_grab_kind.py) | `BoxGrabKind`: whether a grabbed box is moved or resized. |
| [detection_box_item.py](./detection_box_item.py) | `DetectionBoxItem`: box of one detection styled by its role and the display options, highlightable. |
| [reference_box_item.py](./reference_box_item.py) | `ReferenceBoxItem`: dashed outline and label of a reference box, with round corner handles while editable. |
| [detection_label_item.py](./detection_label_item.py) | `DetectionLabelItem`: zoom-independent class and confidence label. |
