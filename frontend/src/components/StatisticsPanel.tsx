import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { HistogramPayload, Profile, StatisticsPayload, Thresholds } from "../api/types";
import { minimumOf } from "../lib/detectionTable";
import { NumberField } from "./NumberField";

interface StatisticsPanelProps {
  refreshToken: string;
  thresholds: Thresholds;
  classColors: Record<string, string>;
  profiles: Profile[];
  shownKey: string | null;
  comparedKey: string | null;
  onThresholdsChange: (thresholds: Thresholds) => void;
  onCompare: (key: string | null) => void;
  onClose: () => void;
}

function formatConfidence(value: number | null): string {
  return value === null ? "–" : value.toFixed(3);
}

function Histogram({ histogram, minimum, color }: { histogram: HistogramPayload; minimum: number; color: string }) {
  const width = 520;
  const height = 150;
  const bottom = 18;
  const largest = Math.max(1, ...histogram.bin_counts);
  const barWidth = width / histogram.bin_counts.length;
  return (
    <svg className="histogram" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      {histogram.bin_counts.map((count, index) => {
        const barHeight = ((height - bottom - 4) * count) / largest;
        const isBelow = (index + 1) * histogram.bin_width <= minimum + 1e-9;
        return (
          <g key={index}>
            <rect
              x={index * barWidth + 1}
              y={height - bottom - barHeight}
              width={barWidth - 2}
              height={barHeight}
              fill={color}
              opacity={isBelow ? 0.3 : 0.85}
            >
              <title>
                {(index * histogram.bin_width).toFixed(2)}–{((index + 1) * histogram.bin_width).toFixed(2)}: {count}
              </title>
            </rect>
          </g>
        );
      })}
      {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
        <text key={tick} x={Math.min(width - 14, tick * width)} y={height - 4} fontSize={10} fill="var(--text-muted)">
          {tick.toFixed(2)}
        </text>
      ))}
      {minimum > 0 && (
        <line
          x1={minimum * width}
          x2={minimum * width}
          y1={0}
          y2={height - bottom}
          stroke="var(--danger)"
          strokeWidth={2}
          strokeDasharray="4 3"
        />
      )}
    </svg>
  );
}

export function StatisticsPanel({
  refreshToken,
  thresholds,
  classColors,
  profiles,
  shownKey,
  comparedKey,
  onThresholdsChange,
  onCompare,
  onClose,
}: StatisticsPanelProps) {
  const [payload, setPayload] = useState<StatisticsPayload | null>(null);
  const [error, setError] = useState("");
  const [selectedClass, setSelectedClass] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;
    const timer = window.setTimeout(() => {
      api
        .statistics()
        .then((loaded) => {
          if (!isCurrent) return;
          setPayload(loaded);
          setError("");
        })
        .catch((caught: unknown) => isCurrent && setError(errorMessage(caught)));
    }, 150);
    return () => {
      isCurrent = false;
      window.clearTimeout(timer);
    };
  }, [refreshToken]);

  const statistics = payload?.statistics ?? null;
  const selected = statistics?.classes.find((entry) => entry.class_name === selectedClass) ?? null;
  const histogram = selected?.histogram ?? statistics?.histogram ?? null;
  const histogramMinimum = selected === null ? thresholds.default_minimum : minimumOf(thresholds, selected.class_name);
  const setClassMinimum = (className: string, value: number | null) => {
    const classMinimums = { ...thresholds.class_minimums };
    if (value === null) delete classMinimums[className];
    else classMinimums[className] = value;
    onThresholdsChange({ ...thresholds, class_minimums: classMinimums });
  };

  return (
    <div
      className="dialog"
      style={{ position: "fixed", right: 16, top: 56, bottom: 44, width: "min(700px, calc(100vw - 32px))", zIndex: 40 }}
      role="dialog"
    >
      <div className="dialog-header">
        <span className="grow">Statistics</span>
        <button className="ghost icon" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </div>
      <div className="dialog-body" style={{ flex: 1 }}>
        {error !== "" && <div className="error-text">{error}</div>}
        <div className="muted">
          {payload?.model ?? "No results shown."}
          {statistics !== null &&
            ` · ${statistics.detected_image_count} of ${statistics.image_count} open images detected`}
        </div>
        <div className="row">
          <span>Default minimum confidence</span>
          <NumberField
            value={thresholds.default_minimum}
            onCommit={(value) => onThresholdsChange({ ...thresholds, default_minimum: value })}
            width={90}
          />
          <span className="hint">Detections below it are hidden and not exported.</span>
        </div>
        <div className="table-wrap" style={{ flex: "none", maxHeight: 260, border: "1px solid var(--border)", borderRadius: 6 }}>
          <table className="grid">
            <colgroup>
              <col style={{ width: 120 }} />
              <col style={{ width: 54 }} />
              <col style={{ width: 70 }} />
              <col style={{ width: 62 }} />
              <col style={{ width: 70 }} />
              <col style={{ width: 44 }} />
              <col style={{ width: 50 }} />
              <col style={{ width: 54 }} />
              <col style={{ width: 118 }} />
            </colgroup>
            <thead>
              <tr>
                <th>Class</th>
                <th>Images</th>
                <th>Detections</th>
                <th>Rejected</th>
                <th>Below min.</th>
                <th>Kept</th>
                <th>Mean</th>
                <th>Median</th>
                <th>Min. Confidence</th>
              </tr>
            </thead>
            <tbody>
              {statistics?.classes.map((entry) => (
                <tr
                  key={entry.class_name}
                  className={entry.class_name === selectedClass ? "selected" : ""}
                  onClick={() => setSelectedClass(entry.class_name === selectedClass ? null : entry.class_name)}
                >
                  <td>
                    <span
                      className="swatch"
                      style={{
                        background: classColors[entry.class_name] ?? "var(--border-strong)",
                        display: "inline-block",
                        marginRight: 5,
                        verticalAlign: -1,
                      }}
                    />
                    {entry.class_name}
                  </td>
                  <td className="number">{entry.image_count}</td>
                  <td className="number">{entry.detection_count}</td>
                  <td className="number">{entry.rejected_count}</td>
                  <td className="number">{entry.below_minimum_count}</td>
                  <td className="number">{entry.kept_count}</td>
                  <td className="number">{formatConfidence(entry.mean_confidence)}</td>
                  <td className="number">{formatConfidence(entry.median_confidence)}</td>
                  <td onClick={(event) => event.stopPropagation()}>
                    <div className="row">
                      <input
                        type="checkbox"
                        title="Use an own minimum instead of the default"
                        checked={thresholds.class_minimums[entry.class_name] !== undefined}
                        onChange={(event) =>
                          setClassMinimum(entry.class_name, event.target.checked ? thresholds.default_minimum : null)
                        }
                      />
                      {thresholds.class_minimums[entry.class_name] !== undefined ? (
                        <NumberField
                          value={thresholds.class_minimums[entry.class_name] ?? 0}
                          onCommit={(value) => setClassMinimum(entry.class_name, value)}
                          width={60}
                        />
                      ) : (
                        <span className="faint small">Default</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {histogram !== null && (
          <div>
            <div className="small muted">
              Confidence histogram of {selected === null ? "every class" : selected.class_name}; the dashed line marks the
              minimum.
            </div>
            <Histogram
              histogram={histogram}
              minimum={histogramMinimum}
              color={selected === null ? "var(--accent)" : (classColors[selected.class_name] ?? "var(--accent)")}
            />
          </div>
        )}
        <div className="row">
          <span>Compare with</span>
          <select
            className="grow"
            value={comparedKey ?? ""}
            onChange={(event) => onCompare(event.target.value === "" ? null : event.target.value)}
          >
            <option value="">None</option>
            {profiles
              .filter((profile) => profile.key !== shownKey)
              .map((profile) => (
                <option key={profile.key} value={profile.key}>
                  {profile.model_name} ({profile.options_text})
                </option>
              ))}
          </select>
        </div>
        {payload?.comparison != null && (
          <>
            <div className="hint">
              {payload.comparison.image_count} images detected by both; detections paired by IoU ≥{" "}
              {payload.comparison.iou_threshold}. The compared boxes are drawn dotted on the image.
            </div>
            <div className="table-wrap" style={{ flex: "none", maxHeight: 220, border: "1px solid var(--border)", borderRadius: 6 }}>
              <table className="grid">
                <thead>
                  <tr>
                    <th>Class</th>
                    <th>Shown</th>
                    <th>Compared</th>
                    <th>Matched</th>
                    <th>Only shown</th>
                    <th>Only compared</th>
                  </tr>
                </thead>
                <tbody>
                  {payload.comparison.classes.map((entry) => (
                    <tr key={entry.class_name}>
                      <td>{entry.class_name}</td>
                      <td className="number">{entry.baseline_count}</td>
                      <td className="number">{entry.candidate_count}</td>
                      <td className="number">{entry.matched_count}</td>
                      <td className="number">{entry.baseline_only_count}</td>
                      <td className="number">{entry.candidate_only_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
