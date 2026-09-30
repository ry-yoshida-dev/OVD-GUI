import { api } from "../api/client";
import type { WorkspaceState } from "../api/types";

interface StatusBarProps {
  state: WorkspaceState;
  localMessage: string | null;
  upload: { done: number; total: number } | null;
  onCancel: () => void;
}

export function StatusBar({ state, localMessage, upload, onCancel }: StatusBarProps) {
  const progress = state.progress;
  const isWorking = progress !== null || state.activity !== "";
  return (
    <div className="statusbar">
      <span className="message" title={localMessage ?? state.status.message}>
        {localMessage ?? state.status.message}
      </span>
      {state.summary !== "" && (
        <span className="summary" title={state.summary}>
          {state.summary}
        </span>
      )}
      {upload !== null && (
        <span className="progress">
          Uploading {upload.done}/{upload.total}
          <span className="progress-bar">
            <div style={{ width: `${(100 * upload.done) / Math.max(1, upload.total)}%` }} />
          </span>
        </span>
      )}
      {isWorking && (
        <span className="progress">
          <span className="muted" style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {progress === null
              ? state.activity
              : `${progress.title} ${progress.processed_count}/${progress.total_count}`}
          </span>
          <span className={`progress-bar${progress === null ? " indeterminate" : ""}`}>
            <div
              style={{
                width:
                  progress === null ? undefined : `${(100 * progress.processed_count) / Math.max(1, progress.total_count)}%`,
              }}
            />
          </span>
          {progress !== null && (
            <button className="small" onClick={onCancel}>
              Cancel
            </button>
          )}
        </span>
      )}
      {state.last_export !== null && !isWorking && (
        <a href={api.exportDownloadUrl} title={`Download ${state.last_export.output_directory} as a ZIP file`}>
          Download last export
        </a>
      )}
    </div>
  );
}
