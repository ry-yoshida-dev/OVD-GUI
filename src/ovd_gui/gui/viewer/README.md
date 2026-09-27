# viewer

## Overview

Zoomable image view drawing detection and reference boxes over the image, also used to draw and adjust reference
rectangles.

## Components

| Component | Description |
| --------- | ----------- |
| [image_canvas.py](./image_canvas.py) | `ImageCanvas`: zoomable view of a PIL image with detection and reference boxes; draws rectangles, and moves and resizes reference boxes, in drawing mode. |
| [box_grab.py](./box_grab.py) | `BoxGrab`: reference box held by the mouse and the fixed point of the drag. |
| [box_grab_kind.py](./box_grab_kind.py) | `BoxGrabKind`: whether a grabbed box is moved or resized. |
| [detection_box_item.py](./detection_box_item.py) | `DetectionBoxItem`: box of one detection, highlightable. |
| [reference_box_item.py](./reference_box_item.py) | `ReferenceBoxItem`: dashed outline and label of a reference box, with round corner handles while editable. |
| [detection_label_item.py](./detection_label_item.py) | `DetectionLabelItem`: zoom-independent class and confidence label. |
