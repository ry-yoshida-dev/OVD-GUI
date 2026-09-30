import type { Detection, DetectionsPayload, Thresholds } from "../api/types";

export type ColumnKey = "keep" | "image" | "class" | "query" | "confidence" | "x1" | "y1" | "x2" | "y2";

export type ColumnKind = "values" | "range";

export interface ColumnDefinition {
  key: ColumnKey;
  label: string;
  kind: ColumnKind;
  width: number;
}

export const COLUMNS: ColumnDefinition[] = [
  { key: "keep", label: "Keep", kind: "values", width: 52 },
  { key: "image", label: "Image", kind: "values", width: 150 },
  { key: "class", label: "Class", kind: "values", width: 110 },
  { key: "query", label: "Query", kind: "values", width: 110 },
  { key: "confidence", label: "Confidence", kind: "range", width: 86 },
  { key: "x1", label: "x1", kind: "range", width: 58 },
  { key: "y1", label: "y1", kind: "range", width: 58 },
  { key: "x2", label: "x2", kind: "range", width: 58 },
  { key: "y2", label: "y2", kind: "range", width: 58 },
];

export type ColumnCondition =
  | { kind: "values"; values: string[] }
  | { kind: "range"; minimum: number | null; maximum: number | null };

export type TableFilter = Partial<Record<ColumnKey, ColumnCondition>>;

export interface SortOrder {
  key: ColumnKey;
  isDescending: boolean;
}

interface RowBase {
  key: string;
  imagePath: string;
  imageName: string;
  imageOrder: number;
  outdated: string | null;
}

export interface DetectionRow extends RowBase {
  kind: "detection";
  detection: Detection;
}

export interface StatusRow extends RowBase {
  kind: "status";
  text: string;
}

export type TableRow = DetectionRow | StatusRow;

export const KEPT_TEXT = "Kept";
export const REJECTED_TEXT = "Rejected";

export function minimumOf(thresholds: Thresholds, className: string): number {
  return thresholds.class_minimums[className] ?? thresholds.default_minimum;
}

export function buildRows(payload: DetectionsPayload | null, thresholds: Thresholds): TableRow[] {
  if (payload === null) return [];
  const rows: TableRow[] = [];
  payload.images.forEach((image, imageOrder) => {
    const base = { imagePath: image.path, imageName: image.name, imageOrder, outdated: image.outdated };
    const listed = image.detections.filter(
      (detection) => detection.confidence >= minimumOf(thresholds, detection.class_name),
    );
    if (listed.length === 0) {
      rows.push({
        ...base,
        kind: "status",
        key: `${image.path}#status`,
        text: image.is_detected ? "No detections" : "Not analyzed",
      });
      return;
    }
    for (const detection of listed) {
      rows.push({ ...base, kind: "detection", key: `${image.path}#${detection.index}`, detection });
    }
  });
  return rows;
}

export function cellValue(row: TableRow, key: ColumnKey): string | number | null {
  if (key === "image") return row.imageName;
  if (row.kind === "status") return null;
  const detection = row.detection;
  switch (key) {
    case "keep":
      return detection.is_accepted ? KEPT_TEXT : REJECTED_TEXT;
    case "class":
      return detection.class_name;
    case "query":
      return detection.query;
    case "confidence":
      return detection.confidence;
    case "x1":
      return detection.box[0];
    case "y1":
      return detection.box[1];
    case "x2":
      return detection.box[2];
    case "y2":
      return detection.box[3];
  }
}

function passes(row: TableRow, key: ColumnKey, condition: ColumnCondition): boolean {
  const value = cellValue(row, key);
  if (value === null) return false;
  if (condition.kind === "values") return condition.values.includes(String(value));
  const number = Number(value);
  return (
    (condition.minimum === null || number >= condition.minimum) &&
    (condition.maximum === null || number <= condition.maximum)
  );
}

export function filterRows(rows: TableRow[], filter: TableFilter): TableRow[] {
  const conditions = Object.entries(filter) as [ColumnKey, ColumnCondition][];
  if (conditions.length === 0) return rows;
  return rows.filter((row) => conditions.every(([key, condition]) => passes(row, key, condition)));
}

export function sortRows(rows: TableRow[], order: SortOrder | null): TableRow[] {
  if (order === null) return rows;
  const direction = order.isDescending ? -1 : 1;
  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
  return [...rows].sort((left, right) => {
    const leftValue = cellValue(left, order.key);
    const rightValue = cellValue(right, order.key);
    if (leftValue === null || rightValue === null) {
      if (leftValue === rightValue) return left.imageOrder - right.imageOrder;
      return leftValue === null ? 1 : -1;
    }
    const compared =
      typeof leftValue === "number" && typeof rightValue === "number"
        ? leftValue - rightValue
        : collator.compare(String(leftValue), String(rightValue));
    return compared === 0 ? left.imageOrder - right.imageOrder : compared * direction;
  });
}

export function valuesOf(rows: TableRow[], key: ColumnKey): string[] {
  const values = new Set<string>();
  for (const row of rows) {
    const value = cellValue(row, key);
    if (value !== null) values.add(String(value));
  }
  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
  return [...values].sort(collator.compare);
}

export function spanOf(rows: TableRow[], key: ColumnKey): [number, number] | null {
  let minimum = Number.POSITIVE_INFINITY;
  let maximum = Number.NEGATIVE_INFINITY;
  for (const row of rows) {
    const value = cellValue(row, key);
    if (typeof value === "number") {
      minimum = Math.min(minimum, value);
      maximum = Math.max(maximum, value);
    }
  }
  return minimum <= maximum ? [minimum, maximum] : null;
}

export function listedIndices(rows: TableRow[]): Map<string, Set<number>> {
  const listed = new Map<string, Set<number>>();
  for (const row of rows) {
    if (row.kind !== "detection") continue;
    let indices = listed.get(row.imagePath);
    if (indices === undefined) {
      indices = new Set();
      listed.set(row.imagePath, indices);
    }
    indices.add(row.detection.index);
  }
  return listed;
}

export function formatNumber(value: number, key: ColumnKey): string {
  return key === "confidence" ? value.toFixed(3) : value.toFixed(1);
}
