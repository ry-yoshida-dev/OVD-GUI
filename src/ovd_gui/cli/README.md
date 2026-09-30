# cli

## Overview

Command line of `ovd-gui`: which interface to start (web by default, the PySide6 window with `--qt`), the images or
folders to open, and where the web server listens.

## Components

| Component | Description |
| --------- | ----------- |
| [command_line.py](./command_line.py) | `CommandLine`: parses `paths`, `--qt`, `--host` (default `127.0.0.1`), `--port` (default `8000`) and `--no-browser`. |
| [launch_options.py](./launch_options.py) | `LaunchOptions`: interface, paths, host, port and whether the browser is opened. |
| [interface_kind.py](./interface_kind.py) | `InterfaceKind`: web server or desktop window. |

## Examples

```python
options: LaunchOptions = CommandLine().parse(["--port", "8080", "--no-browser", "images/"])
```
