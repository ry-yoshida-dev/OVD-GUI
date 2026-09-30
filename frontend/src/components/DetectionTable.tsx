import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  COLUMNS,
  type ColumnCondition,
  type ColumnDefinition,
  type ColumnKey,
  formatNumber,
  type SortOrder,
  type TableFilter,
  type TableRow,
} from "../lib/detectionTable";
import { colorOf } from "../lib/displayOptions";
import { useDialogs } from "./DialogHost";
import { FilterPopup } from "./FilterPopup";
import { useMenu } from "./Menu";

interface DetectionTableProps {
  rows: TableRow[];
  allRows: TableRow[];
  filter: TableFilter;
  onFilterChange: (filter: TableFilter) => void;
  order: SortOrder | null;
  onOrderChange: (order: SortOrder | null) => void;
  currentPath: string | null;
  selectedKey: string | null;
  onSelectRow: (row: TableRow) => void;
  onSetAccepted: (rows: TableRow[], isAccepted: boolean) => void;
  onSaveCsv: () => void;
  onUpdateOutdated: () => void;
  onClearResults: () => void;
  outdatedCount: number;
  hasResults: boolean;
  palette: string[];
}

const ROW_HEIGHT = 25;
const OVERSCAN = 12;

export function DetectionTable({
  rows,
  allRows,
  filter,
  onFilterChange,
  order,
  onOrderChange,
  currentPath,
  selectedKey,
  onSelectRow,
  onSetAccepted,
  onSaveCsv,
  onUpdateOutdated,
  onClearResults,
  outdatedCount,
  hasResults,
  palette,
}: DetectionTableProps) {
  const dialogs = useDialogs();
  const menu = useMenu();
  const scroller = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(400);
  const [popup, setPopup] = useState<{ column: ColumnDefinition; x: number; y: number } | null>(null);

  useLayoutEffect(() => {
    const element = scroller.current;
    if (element === null) return;
    const observer = new ResizeObserver(() => setViewportHeight(element.clientHeight));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (selectedKey === null) return;
    const index = rows.findIndex((row) => row.key === selectedKey);
    const element = scroller.current;
    if (index < 0 || element === null) return;
    const top = index * ROW_HEIGHT;
    const headerHeight = 28;
    if (top < element.scrollTop) element.scrollTop = top;
    else if (top + ROW_HEIGHT > element.scrollTop + element.clientHeight - headerHeight) {
      element.scrollTop = top + ROW_HEIGHT - element.clientHeight + headerHeight;
    }
  }, [selectedKey, rows]);

  const first = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const last = Math.min(rows.length, Math.ceil((scrollTop + viewportHeight) / ROW_HEIGHT) + OVERSCAN);
  const visibleRows = rows.slice(first, last);
  const filteredCount = Object.keys(filter).length;
  const detectionCount = rows.filter((row) => row.kind === "detection").length;

  const setCondition = (key: ColumnKey, condition: ColumnCondition | undefined) => {
    const next = { ...filter };
    if (condition === undefined) delete next[key];
    else next[key] = condition;
    onFilterChange(next);
  };

  const cycleOrder = (key: ColumnKey) => {
    if (order === null || order.key !== key) onOrderChange({ key, isDescending: key === "confidence" });
    else if (order.isDescending === (key === "confidence")) onOrderChange({ key, isDescending: !order.isDescending });
    else onOrderChange(null);
  };

  const listedDetections = rows.filter((row) => row.kind === "detection");

  const openTableMenu = (x: number, y: number) =>
    menu.open(x, y, [
      {
        label: `Keep All Listed (${listedDetections.length})`,
        isDisabled: listedDetections.length === 0,
        onSelect: () => onSetAccepted(listedDetections, true),
      },
      {
        label: `Reject All Listed (${listedDetections.length})`,
        isDisabled: listedDetections.length === 0,
        onSelect: () => onSetAccepted(listedDetections, false),
      },
      { isSeparator: true, label: "" },
      { label: "Save Listed as CSV…", isDisabled: listedDetections.length === 0, onSelect: onSaveCsv },
      { label: "Clear Filters", isDisabled: filteredCount === 0, onSelect: () => onFilterChange({}) },
    ]);

  const moveSelection = (delta: number) => {
    const index = rows.findIndex((row) => row.key === selectedKey);
    const next = rows[Math.max(0, Math.min(rows.length - 1, (index < 0 ? -1 : index) + delta))];
    if (next !== undefined) onSelectRow(next);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: 0, height: "100%" }}>
      <div className="panel-title">
        <span className="grow">Detections</span>
        <span className="muted small">
          {detectionCount} listed{filteredCount > 0 ? ` · ${filteredCount} filters` : ""}
        </span>
      </div>
      <div
        ref={scroller}
        className="table-wrap"
        tabIndex={0}
        onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
        onContextMenu={(event) => {
          event.preventDefault();
          openTableMenu(event.clientX, event.clientY);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            moveSelection(1);
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            moveSelection(-1);
          } else if (event.key === " ") {
            event.preventDefault();
            const row = rows.find((candidate) => candidate.key === selectedKey);
            if (row?.kind === "detection") onSetAccepted([row], !row.detection.is_accepted);
          }
        }}
      >
        <table className="grid">
          <colgroup>
            {COLUMNS.map((column) => (
              <col key={column.key} style={{ width: column.width }} />
            ))}
          </colgroup>
          <thead>
            <tr>
              {COLUMNS.map((column) => (
                <th
                  key={column.key}
                  title="Click to sort; right-click to filter"
                  onClick={() => cycleOrder(column.key)}
                  onContextMenu={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    setPopup({ column, x: event.clientX, y: event.clientY });
                  }}
                >
                  {column.label}
                  {order?.key === column.key && (order.isDescending ? " ▾" : " ▴")}
                  {filter[column.key] !== undefined && (
                    <span
                      className="funnel"
                      onClick={(event) => {
                        event.stopPropagation();
                        setPopup({ column, x: event.clientX, y: event.clientY });
                      }}
                    >
                      ⏷
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr className="status">
                <td colSpan={COLUMNS.length}>
                  {allRows.length === 0 ? "Open images to list their detections." : "No detection passes the filters."}
                </td>
              </tr>
            )}
            {first > 0 && (
              <tr style={{ height: first * ROW_HEIGHT }}>
                <td colSpan={COLUMNS.length} style={{ padding: 0, border: 0 }} />
              </tr>
            )}
            {visibleRows.map((row) => {
              const isCurrent = row.imagePath === currentPath;
              const isSelected = row.key === selectedKey;
              const classes = [
                isSelected ? "selected" : isCurrent ? "current" : "",
                row.kind === "status" ? "status" : row.detection.is_accepted ? "" : "rejected",
              ].join(" ");
              return (
                <tr key={row.key} className={classes} onClick={() => onSelectRow(row)} style={{ height: ROW_HEIGHT }}>
                  <td>
                    {row.kind === "detection" && (
                      <input
                        type="checkbox"
                        checked={row.detection.is_accepted}
                        title="Checked detections are exported; uncheck to reject this detection"
                        onClick={(event) => event.stopPropagation()}
                        onChange={(event) => onSetAccepted([row], event.target.checked)}
                      />
                    )}
                  </td>
                  <td
                    className={row.kind === "detection" ? "strike" : ""}
                    title={row.outdated === null ? row.imagePath : `${row.imagePath}\nDetected with other classes: ${row.outdated}`}
                  >
                    {row.outdated !== null && <span style={{ color: "var(--warning)", marginRight: 4 }}>⚠</span>}
                    {row.imageName}
                  </td>
                  {row.kind === "status" ? (
                    <td colSpan={COLUMNS.length - 2}>{row.text}</td>
                  ) : (
                    <>
                      <td className="strike">
                        <span
                          className="swatch"
                          style={{
                            background: colorOf(palette, row.detection.class_id),
                            display: "inline-block",
                            marginRight: 5,
                            verticalAlign: -1,
                          }}
                        />
                        {row.detection.class_name}
                      </td>
                      <td className="strike">{row.detection.query}</td>
                      <td className="number">{formatNumber(row.detection.confidence, "confidence")}</td>
                      {row.detection.box.map((value, index) => (
                        <td key={index} className="number">
                          {formatNumber(value, "x1")}
                        </td>
                      ))}
                    </>
                  )}
                </tr>
              );
            })}
            {last < rows.length && (
              <tr style={{ height: (rows.length - last) * ROW_HEIGHT }}>
                <td colSpan={COLUMNS.length} style={{ padding: 0, border: 0 }} />
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="panel-footer">
        <button
          onClick={(event) => {
            const bounds = event.currentTarget.getBoundingClientRect();
            menu.openBelow(
              event.currentTarget,
              COLUMNS.map((column) => ({
                label: column.label,
                isChecked: filter[column.key] !== undefined,
                onSelect: () => setPopup({ column, x: bounds.left, y: bounds.top - 320 }),
              })),
            );
          }}
        >
          Filter{filteredCount > 0 ? ` (${filteredCount})` : ""}
        </button>
        <button onClick={() => onFilterChange({})} disabled={filteredCount === 0}>
          Clear Filters
        </button>
        <button onClick={onUpdateOutdated} disabled={outdatedCount === 0} title="Detect again the images marked outdated">
          Update Outdated{outdatedCount > 0 ? ` (${outdatedCount})` : ""}
        </button>
        <span className="grow" />
        <button onClick={onSaveCsv} disabled={detectionCount === 0}>
          Save CSV…
        </button>
        <button
          className="danger"
          disabled={!hasResults}
          onClick={async () => {
            const isConfirmed = await dialogs.confirm({
              title: "Clear Results",
              message: "Forget the stored results of every model?",
              confirmLabel: "Clear",
              isDanger: true,
            });
            if (isConfirmed) onClearResults();
          }}
        >
          Clear Results
        </button>
      </div>
      {popup !== null && (
        <FilterPopup
          column={popup.column}
          rows={allRows}
          condition={filter[popup.column.key]}
          x={popup.x}
          y={popup.y}
          onApply={(condition) => setCondition(popup.column.key, condition)}
          onClose={() => setPopup(null)}
        />
      )}
      {menu.element}
    </div>
  );
}
