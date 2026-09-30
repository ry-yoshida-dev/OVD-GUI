export type Box = [number, number, number, number];

export type ImageStateValue = "not_analyzed" | "detected" | "outdated" | "failed";

export interface ImageEntry {
  path: string;
  name: string;
  state: ImageStateValue;
  color: string;
  is_marked_filled: boolean;
  count_text: string;
  description: string;
}

export interface Detection {
  index: number;
  class_id: number;
  class_name: string;
  query: string;
  confidence: number;
  box: Box;
  is_accepted: boolean;
}

export interface CurrentImage {
  path: string;
  name: string;
  version: string | null;
  width: number | null;
  height: number | null;
  compared_model_name: string | null;
  compared_detections: Detection[];
}

export interface PresetEntry {
  name: string;
  label: string;
}

export interface BackendEntry {
  value: string;
  is_image_prompt_supported: boolean;
  presets: PresetEntry[];
}

export interface DeviceEntry {
  value: string;
  is_available: boolean;
  is_half_precision_supported: boolean;
}

export interface ModelSelection {
  backend: string;
  preset_name: string;
  device: string;
  is_half_precision_enabled: boolean;
  confidence_threshold: number;
  nms_iou_threshold: number | null;
}

export interface ModelState {
  backends: BackendEntry[];
  devices: DeviceEntry[];
  selection: ModelSelection;
}

export interface Profile {
  key: string;
  backend: string;
  model_name: string;
  weights_path: string;
  device: string;
  precision: string;
  confidence: string;
  nms: string;
  options_text: string;
  image_count: number;
  outdated_image_count: number;
  detection_count: number;
}

export interface ReferenceEntry {
  name: string;
  digest: string;
  width: number;
  height: number;
  boxes: Box[];
}

export interface ClassEntry {
  name: string;
  color: string;
  phrases: string[];
  references: ReferenceEntry[];
}

export interface ClassSetState {
  name: string;
  is_edited: boolean;
  is_unsaved: boolean;
  names: string[];
  directory: string;
}

export interface Thresholds {
  default_minimum: number;
  class_minimums: Record<string, number>;
}

export interface Progress {
  title: string;
  processed_count: number;
  total_count: number;
  is_blocking: boolean;
}

export interface ExportSummary {
  format_name: string;
  output_directory: string;
  image_count: number;
  detection_count: number;
  file_count: number;
}

export interface WorkspaceState {
  images: ImageEntry[];
  current_image: CurrentImage | null;
  background_image_path: string | null;
  model: ModelState;
  profiles: Profile[];
  shown_profile_key: string | null;
  compared_profile_key: string | null;
  classes: ClassEntry[];
  class_set: ClassSetState;
  is_image_prompt_supported: boolean;
  thresholds: Thresholds;
  status: { message: string; serial: number };
  activity: string;
  summary: string;
  progress: Progress | null;
  is_busy: boolean;
  last_export: ExportSummary | null;
  palette: string[];
  upload_directory: string;
}

export interface DetectionImage {
  path: string;
  name: string;
  is_detected: boolean;
  outdated: string | null;
  detections: Detection[];
}

export interface DetectionsPayload {
  profile_key: string | null;
  images: DetectionImage[];
}

export type ActionStatus = "done" | "rejected" | "needs_approval";

export interface ActionReply {
  status: ActionStatus;
  message: string;
  skipped_class_names: string[];
}

export interface HistogramPayload {
  bin_counts: number[];
  bin_width: number;
}

export interface ClassStatisticsPayload {
  class_name: string;
  image_count: number;
  detection_count: number;
  rejected_count: number;
  below_minimum_count: number;
  kept_count: number;
  mean_confidence: number | null;
  median_confidence: number | null;
  histogram: HistogramPayload;
}

export interface ClassComparisonPayload {
  class_name: string;
  baseline_count: number;
  candidate_count: number;
  matched_count: number;
  baseline_only_count: number;
  candidate_only_count: number;
}

export interface StatisticsPayload {
  model: string | null;
  statistics: {
    image_count: number;
    detected_image_count: number;
    classes: ClassStatisticsPayload[];
    histogram: HistogramPayload;
  } | null;
  comparison: {
    image_count: number;
    iou_threshold: number;
    classes: ClassComparisonPayload[];
  } | null;
}

export interface ClassSetListEntry {
  name: string;
  saved_at: string;
  is_readable: boolean;
  class_names: string[];
  description: string;
}

export interface ClassSetPreview {
  name: string;
  classes: ClassEntry[];
}

export interface DirectoryListing {
  path: string;
  parent: string | null;
  directories: string[];
  images: string[];
  shortcuts: { name: string; path: string }[];
}

export interface ExportFormat {
  value: string;
  label: string;
  is_confidence_supported: boolean;
}

export interface ExportPlan {
  model_name: string;
  options_text: string;
  image_count: number;
  pending_count: number;
  issue: string;
  formats: ExportFormat[];
  scopes: { value: string; label: string; description: string }[];
  default_directory: string;
}

export interface ReferenceDraft {
  draft_id: string;
  name: string;
  width: number;
  height: number;
}

export type WorkspaceTopic = "state" | "detections" | "class_sets";

export type ServerEvent =
  | { type: "changed"; topics: WorkspaceTopic[] }
  | { type: "notice"; level: "info" | "error"; title: string; message: string };
