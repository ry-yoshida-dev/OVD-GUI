import type { ModelSelection, ModelState } from "../api/types";
import { NumberField } from "./NumberField";

interface ModelPanelProps {
  model: ModelState;
  isDisabled: boolean;
  onSelectPreset: (backend: string, presetName: string) => void;
  onChange: (selection: ModelSelection) => void;
}

export function ModelPanel({ model, isDisabled, onSelectPreset, onChange }: ModelPanelProps) {
  const selection = model.selection;
  const backend = model.backends.find((entry) => entry.value === selection.backend);
  const device = model.devices.find((entry) => entry.value === selection.device);
  const isHalfPrecisionSupported = device?.is_half_precision_supported ?? false;
  const change = (update: Partial<ModelSelection>) => onChange({ ...selection, ...update });
  return (
    <div className="form-grid">
      <span>Backend</span>
      <select
        value={selection.backend}
        disabled={isDisabled}
        onChange={(event) => {
          const next = model.backends.find((entry) => entry.value === event.target.value);
          const firstPreset = next?.presets[0];
          if (next !== undefined && firstPreset !== undefined) onSelectPreset(next.value, firstPreset.name);
        }}
      >
        {model.backends.map((entry) => (
          <option key={entry.value} value={entry.value}>
            {entry.value}
            {entry.is_image_prompt_supported ? " (text + image)" : ""}
          </option>
        ))}
      </select>
      <span>Preset</span>
      <select
        value={selection.preset_name}
        disabled={isDisabled}
        onChange={(event) => onSelectPreset(selection.backend, event.target.value)}
      >
        {(backend?.presets ?? []).map((preset) => (
          <option key={preset.name} value={preset.name}>
            {preset.name}
          </option>
        ))}
      </select>
      <span>Device</span>
      <select
        value={selection.device}
        disabled={isDisabled}
        onChange={(event) => {
          const next = model.devices.find((entry) => entry.value === event.target.value);
          change({
            device: event.target.value,
            is_half_precision_enabled:
              selection.is_half_precision_enabled && (next?.is_half_precision_supported ?? false),
          });
        }}
      >
        {model.devices.map((entry) => (
          <option key={entry.value} value={entry.value} disabled={!entry.is_available}>
            {entry.value}
            {entry.is_available ? "" : " (unavailable)"}
          </option>
        ))}
      </select>
      <span>Precision</span>
      <label title={isHalfPrecisionSupported ? "Run the model in float16" : "float16 needs a GPU"}>
        <input
          type="checkbox"
          checked={selection.is_half_precision_enabled}
          disabled={isDisabled || !isHalfPrecisionSupported}
          onChange={(event) => change({ is_half_precision_enabled: event.target.checked })}
        />
        float16
      </label>
      <span>Confidence</span>
      <NumberField
        value={selection.confidence_threshold}
        isDisabled={isDisabled}
        onCommit={(value) => change({ confidence_threshold: value })}
      />
      <span>NMS</span>
      <div className="row">
        <label>
          <input
            type="checkbox"
            checked={selection.nms_iou_threshold !== null}
            disabled={isDisabled}
            onChange={(event) => change({ nms_iou_threshold: event.target.checked ? 0.5 : null })}
          />
          IoU
        </label>
        <div className="grow" style={{ display: "flex" }}>
          <NumberField
            value={selection.nms_iou_threshold ?? 0.5}
            isDisabled={isDisabled || selection.nms_iou_threshold === null}
            onCommit={(value) => change({ nms_iou_threshold: value })}
            width={90}
          />
        </div>
      </div>
    </div>
  );
}
