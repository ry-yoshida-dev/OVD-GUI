# preset

## Overview

Model presets: YAML files whose `detector` section maps onto `DetectorSettings`, built with `DataclassInitializer`.

## Components

| Component | Description |
| --------- | ----------- |
| [model_preset.py](./model_preset.py) | `ModelPreset`: one preset file and its conversion into `DetectorSettings`. |
| [preset_catalog.py](./preset_catalog.py) | `PresetCatalog`: presets discovered from `<root>/<backend>/<name>.yaml`, by default those bundled with `open_vocabulary_detector`. |

## Examples

```python
catalog = PresetCatalog.from_package()
settings = catalog.presets_of(DetectorBackend.YOLOE)[0].load_settings()
```
