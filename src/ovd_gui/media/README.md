# media

## Overview

Image files handled by the application, independent of Qt: reading them upright and gathering them from paths
chosen or dropped by the user.

## Components

| Component | Description |
| --------- | ----------- |
| [loaded_image.py](./loaded_image.py) | `LoadedImage`: EXIF-upright RGB image read from disk, and the supported file formats. |
| [image_collection.py](./image_collection.py) | `ImageCollection`: new images found in dropped or chosen paths, with skipped counts. |
