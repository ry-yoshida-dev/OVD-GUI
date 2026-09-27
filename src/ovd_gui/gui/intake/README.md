# intake

## Overview

Widgets through which images enter the application by drag and drop; the drop itself is handled by the enclosing
window (`MainWindow`, or the reference image picker).

## Components

| Component | Description |
| --------- | ----------- |
| [drop_zone.py](./drop_zone.py) | `DropZone`: placeholder inviting drops under a configurable title, with open buttons. |
| [drop_overlay.py](./drop_overlay.py) | `DropOverlay`: translucent drag-over layer previewing what a drop adds. |
