# sidebar

## Overview

Left side of the window: a scrollable stack of collapsible sections and the panels shown in them.

## Components

| Component | Description |
| --------- | ----------- |
| [section_stack.py](./section_stack.py) | `SectionStack`: scrollable stack of collapsible sections sharing the spare height. |
| [collapsible_section.py](./collapsible_section.py) | `CollapsibleSection`: titled section folded by clicking its header. |
| [settings_panel.py](./settings_panel.py) | `SettingsPanel`: backend/preset selection and per-run overrides producing `DetectorSettings`. |
| [image_list_panel.py](./image_list_panel.py) | `ImageListPanel`: open images in the order added, and the current one. |
