# sidebar

## Overview

Left side of the window: a scrollable stack of collapsible sections and the panels shown in them.

## Components

| Component | Description |
| --------- | ----------- |
| [section_stack.py](./section_stack.py) | `SectionStack`: scrollable stack of collapsible sections sharing the spare height. |
| [collapsible_section.py](./collapsible_section.py) | `CollapsibleSection`: titled section folded by clicking its header. |
| [settings_panel.py](./settings_panel.py) | `SettingsPanel`: backend/preset selection and per-run overrides producing `DetectorSettings`. |
| [image_list_panel.py](./image_list_panel.py) | `ImageListPanel`: open images in the order added with their `ImageStatus` (from [workspace](../../workspace/README.md)) and kept detection count; closes selected images and moves to the previous or next one. |
| [status_dot_icon.py](./status_dot_icon.py) | `StatusDotIcon`: filled or outlined dot marking an image state. |
| [image_count_delegate.py](./image_count_delegate.py) | `ImageCountDelegate`: image row with its detection count right-aligned. |
