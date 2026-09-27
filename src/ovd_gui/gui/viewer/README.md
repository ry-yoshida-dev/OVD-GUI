# viewer

## Overview

Zoomable image view drawing detection and reference boxes over the image, also used to draw reference rectangles.

## Components

| Component | Description |
| --------- | ----------- |
| [image_canvas.py](./image_canvas.py) | `ImageCanvas`: zoomable view of a PIL image with detection and reference boxes; draws rectangles in drawing mode. |
| [detection_box_item.py](./detection_box_item.py) | `DetectionBoxItem`: box of one detection, highlightable. |
| [reference_box_item.py](./reference_box_item.py) | `ReferenceBoxItem`: dashed outline and label of a reference box. |
| [detection_label_item.py](./detection_label_item.py) | `DetectionLabelItem`: zoom-independent class and confidence label. |
