import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { ExportPlan } from "../api/types";
import { useStoredState } from "../hooks/useStoredState";
import { Dialog } from "./Dialog";
import { NumberField } from "./NumberField";
import { ServerBrowserDialog } from "./ServerBrowserDialog";

export interface ExportChoice {
  annotation_format: string;
  output_directory: string;
  is_confidence_included: boolean;
  scope: string;
  minimum_confidence: number;
  is_annotated_image_saved: boolean;
}

interface ExportDialogProps {
  onExport: (choice: ExportChoice) => Promise<boolean>;
  onClose: () => void;
}

interface StoredExportOptions {
  annotation_format: string;
  is_confidence_included: boolean;
  scope: string;
  minimum_confidence: number;
  is_annotated_image_saved: boolean;
  output_directory: string;
}

export function ExportDialog({ onExport, onClose }: ExportDialogProps) {
  const [plan, setPlan] = useState<ExportPlan | null>(null);
  const [error, setError] = useState("");
  const [isBrowsing, setIsBrowsing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [stored, setStored] = useStoredState<StoredExportOptions>("ovd-gui.export", {
    annotation_format: "coco",
    is_confidence_included: false,
    scope: "kept",
    minimum_confidence: 0,
    is_annotated_image_saved: false,
    output_directory: "",
  });
  const [outputDirectory, setOutputDirectory] = useState("");

  useEffect(() => {
    api
      .exportPlan()
      .then((loaded) => {
        setPlan(loaded);
        setOutputDirectory(loaded.default_directory);
      })
      .catch((caught: unknown) => setError(errorMessage(caught)));
  }, []);

  const format = plan?.formats.find((entry) => entry.value === stored.annotation_format) ?? plan?.formats[0];
  const change = (update: Partial<StoredExportOptions>) => setStored((current) => ({ ...current, ...update }));

  const submit = async () => {
    if (format === undefined) return;
    setIsSubmitting(true);
    const isDone = await onExport({
      annotation_format: format.value,
      output_directory: outputDirectory,
      is_confidence_included: stored.is_confidence_included && format.is_confidence_supported,
      scope: stored.scope,
      minimum_confidence: stored.minimum_confidence,
      is_annotated_image_saved: stored.is_annotated_image_saved,
    });
    setIsSubmitting(false);
    if (isDone) {
      setStored((current) => ({ ...current, output_directory: outputDirectory }));
      onClose();
    }
  };

  return (
    <>
      <Dialog
        title="Export Detections"
        onClose={onClose}
        width={560}
        footer={
          <>
            <button onClick={onClose}>Cancel</button>
            <button
              className="primary"
              disabled={plan === null || plan.issue !== "" || outputDirectory.trim() === "" || isSubmitting}
              onClick={() => void submit()}
            >
              {plan !== null && plan.pending_count > 0 ? `Detect ${plan.pending_count} and Export` : "Export"}
            </button>
          </>
        }
      >
        {error !== "" && <div className="error-text">{error}</div>}
        {plan !== null && (
          <>
            <div>
              Stored results of <b>{plan.model_name}</b> <span className="muted small">({plan.options_text})</span> on{" "}
              {plan.image_count} open images.
              {plan.pending_count > 0 && (
                <div className="hint">
                  {plan.pending_count} images have no up-to-date result and are detected first.
                </div>
              )}
            </div>
            {plan.issue !== "" && <div className="error-text">{plan.issue}</div>}
            <div className="form-grid">
              <span>Format</span>
              <select value={format?.value ?? ""} onChange={(event) => change({ annotation_format: event.target.value })}>
                {plan.formats.map((entry) => (
                  <option key={entry.value} value={entry.value}>
                    {entry.label}
                  </option>
                ))}
              </select>
              <span>Output folder</span>
              <div className="row">
                <input
                  type="text"
                  className="grow mono"
                  value={outputDirectory}
                  onChange={(event) => setOutputDirectory(event.target.value)}
                  title="Folder on the server"
                />
                <button onClick={() => setIsBrowsing(true)}>Browse…</button>
              </div>
              {stored.output_directory !== "" && stored.output_directory !== outputDirectory && (
                <>
                  <span />
                  <button className="ghost small" style={{ justifySelf: "start" }} onClick={() => setOutputDirectory(stored.output_directory)}>
                    Use last: {stored.output_directory}
                  </button>
                </>
              )}
              <span>Detections</span>
              <div className="row wrap">
                {plan.scopes.map((scope) => (
                  <label key={scope.value} title={scope.description}>
                    <input
                      type="radio"
                      name="scope"
                      checked={stored.scope === scope.value}
                      onChange={() => change({ scope: scope.value })}
                    />
                    {scope.label}
                  </label>
                ))}
              </div>
              <span>Minimum confidence</span>
              <NumberField value={stored.minimum_confidence} onCommit={(value) => change({ minimum_confidence: value })} width={100} />
              <span />
              <label title={format?.is_confidence_supported ? "" : "This format cannot store confidences"}>
                <input
                  type="checkbox"
                  checked={stored.is_confidence_included && (format?.is_confidence_supported ?? false)}
                  disabled={!(format?.is_confidence_supported ?? false)}
                  onChange={(event) => change({ is_confidence_included: event.target.checked })}
                />
                Write confidences
              </label>
              <span />
              <label>
                <input
                  type="checkbox"
                  checked={stored.is_annotated_image_saved}
                  onChange={(event) => change({ is_annotated_image_saved: event.target.checked })}
                />
                Also save the images with boxes drawn (annotated_images/)
              </label>
            </div>
            <div className="hint">
              Rejected detections and those below the class minimums are left out. Files are written on the server;
              download them as a ZIP from the status bar afterwards.
            </div>
          </>
        )}
      </Dialog>
      {isBrowsing && (
        <ServerBrowserDialog
          mode="directory"
          title="Choose Output Folder"
          onChoose={(paths) => {
            const chosen = paths[0];
            if (chosen !== undefined) setOutputDirectory(chosen);
            setIsBrowsing(false);
          }}
          onClose={() => setIsBrowsing(false)}
        />
      )}
    </>
  );
}
