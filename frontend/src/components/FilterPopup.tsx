import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  type ColumnCondition,
  type ColumnDefinition,
  formatNumber,
  spanOf,
  type TableRow,
  valuesOf,
} from "../lib/detectionTable";

interface FilterPopupProps {
  column: ColumnDefinition;
  rows: TableRow[];
  condition: ColumnCondition | undefined;
  x: number;
  y: number;
  onApply: (condition: ColumnCondition | undefined) => void;
  onClose: () => void;
}

function parseBound(text: string): number | null {
  const value = Number.parseFloat(text);
  return text.trim() === "" || Number.isNaN(value) ? null : value;
}

export function FilterPopup({ column, rows, condition, x, y, onApply, onClose }: FilterPopupProps) {
  const reference = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ left: x, top: y });
  const values = useMemo(() => (column.kind === "values" ? valuesOf(rows, column.key) : []), [rows, column]);
  const span = useMemo(() => (column.kind === "range" ? spanOf(rows, column.key) : null), [rows, column]);
  const [checked, setChecked] = useState<Set<string>>(
    () => new Set(condition?.kind === "values" ? condition.values : values),
  );
  const [search, setSearch] = useState("");
  const [minimum, setMinimum] = useState(
    condition?.kind === "range" && condition.minimum !== null ? String(condition.minimum) : "",
  );
  const [maximum, setMaximum] = useState(
    condition?.kind === "range" && condition.maximum !== null ? String(condition.maximum) : "",
  );

  useLayoutEffect(() => {
    const element = reference.current;
    if (element === null) return;
    const bounds = element.getBoundingClientRect();
    setPosition({
      left: Math.max(4, Math.min(x, window.innerWidth - bounds.width - 8)),
      top: Math.max(4, Math.min(y, window.innerHeight - bounds.height - 8)),
    });
  }, [x, y]);

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!reference.current?.contains(event.target as Node)) onClose();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("mousedown", onPointerDown, true);
    window.addEventListener("keydown", onKeyDown, true);
    return () => {
      window.removeEventListener("mousedown", onPointerDown, true);
      window.removeEventListener("keydown", onKeyDown, true);
    };
  }, [onClose]);

  const shownValues = values.filter((value) => value.toLowerCase().includes(search.toLowerCase()));

  const apply = () => {
    if (column.kind === "values") {
      onApply(checked.size === values.length ? undefined : { kind: "values", values: [...checked] });
    } else {
      const lower = parseBound(minimum);
      const upper = parseBound(maximum);
      onApply(lower === null && upper === null ? undefined : { kind: "range", minimum: lower, maximum: upper });
    }
    onClose();
  };

  return (
    <div className="popover" ref={reference} style={position}>
      <div style={{ fontWeight: 600 }}>Filter {column.label}</div>
      {column.kind === "values" ? (
        <>
          <input type="search" placeholder="Search" value={search} autoFocus onChange={(event) => setSearch(event.target.value)} />
          <div className="row small">
            <button className="ghost" onClick={() => setChecked(new Set([...checked, ...shownValues]))}>
              Select all
            </button>
            <button
              className="ghost"
              onClick={() => setChecked(new Set([...checked].filter((value) => !shownValues.includes(value))))}
            >
              Select none
            </button>
          </div>
          <div className="checklist">
            {shownValues.length === 0 && <div className="faint small" style={{ padding: "2px 8px" }}>No values</div>}
            {shownValues.map((value) => (
              <label key={value}>
                <input
                  type="checkbox"
                  checked={checked.has(value)}
                  onChange={(event) => {
                    const next = new Set(checked);
                    if (event.target.checked) next.add(value);
                    else next.delete(value);
                    setChecked(next);
                  }}
                />
                <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{value}</span>
              </label>
            ))}
          </div>
        </>
      ) : (
        <>
          <div className="form-grid">
            <span>At least</span>
            <input
              type="number"
              autoFocus
              value={minimum}
              step="any"
              placeholder={span === null ? "" : formatNumber(span[0], column.key)}
              onChange={(event) => setMinimum(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && apply()}
            />
            <span>At most</span>
            <input
              type="number"
              value={maximum}
              step="any"
              placeholder={span === null ? "" : formatNumber(span[1], column.key)}
              onChange={(event) => setMaximum(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && apply()}
            />
          </div>
          {span !== null && (
            <div className="hint">
              Values range from {formatNumber(span[0], column.key)} to {formatNumber(span[1], column.key)}.
            </div>
          )}
        </>
      )}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button
          onClick={() => {
            onApply(undefined);
            onClose();
          }}
          disabled={condition === undefined}
        >
          Clear
        </button>
        <button className="primary" onClick={apply}>
          Apply
        </button>
      </div>
    </div>
  );
}
