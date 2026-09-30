# web

## Overview

Tests of `ovd_gui.web` through the FastAPI `TestClient`, with a stub detector instead of model weights.

## Components

| Component | Description |
| --------- | ----------- |
| [test_web_application.py](./test_web_application.py) | State with default classes and model settings, background detection of an opened folder, uploads, class edit errors answered with their message, classes replaced as text and saved as a set, refused detection without images, server folder listings, requests without the access cookie refused, and the export download holding only the written files. |
