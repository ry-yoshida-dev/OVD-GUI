import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, errorMessage } from "./api/client";
import type { ActionReply, Detection, ModelSelection, Thresholds } from "./api/types";
import { ClassEditor } from "./components/ClassEditor";
import { ClassSetDialog } from "./components/ClassSetDialog";
import { ClassTextDialog } from "./components/ClassTextDialog";
import { DetectionTable } from "./components/DetectionTable";
import { DetectionViewer } from "./components/DetectionViewer";
import { useDialogs } from "./components/DialogHost";
import { type ExportChoice, ExportDialog } from "./components/ExportDialog";
import { ImageList } from "./components/ImageList";
import { useMenu } from "./components/Menu";
import { ModelPanel } from "./components/ModelPanel";
import { ProfileTable } from "./components/ProfileTable";
import { ReferenceDialog } from "./components/ReferenceDialog";
import { Section } from "./components/Section";
import { ServerBrowserDialog } from "./components/ServerBrowserDialog";
import { Splitter } from "./components/Splitter";
import { StatisticsPanel } from "./components/StatisticsPanel";
import { StatusBar } from "./components/StatusBar";
import { useStoredState } from "./hooks/useStoredState";
import { useWorkspace } from "./hooks/useWorkspace";
import {
  buildRows,
  filterRows,
  listedIndices,
  type SortOrder,
  sortRows,
  type TableFilter,
  type TableRow,
} from "./lib/detectionTable";
import { DEFAULT_DISPLAY_OPTIONS, type DisplayOptions } from "./lib/displayOptions";
import { type DroppedFile, hasFiles, imageFilesOf, imageFilesOfList } from "./lib/droppedFiles";

interface Layout {
  sidebarWidth: number;
  rightWidth: number;
  profileHeight: number;
  collapsedSections: string[];
}

const DEFAULT_LAYOUT: Layout = { sidebarWidth: 320, rightWidth: 520, profileHeight: 170, collapsedSections: [] };
const UPLOAD_CHUNK_SIZE = 16;
const LOCAL_MESSAGE_MILLISECONDS = 7000;

type OpenDialog =
  | { kind: "browse" }
  | { kind: "export" }
  | { kind: "class-sets" }
  | { kind: "class-text" }
  | { kind: "reference"; classIndex: number }
  | null;

function isTyping(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement
  );
}

export function App() {
  const workspace = useWorkspace();
  const { state, detections } = workspace;
  const dialogs = useDialogs();
  const menu = useMenu();
  const [layout, setLayout] = useStoredState<Layout>("ovd-gui.layout", DEFAULT_LAYOUT);
  const [display, setDisplay] = useStoredState<DisplayOptions>("ovd-gui.display", DEFAULT_DISPLAY_OPTIONS);
  const [filter, setFilter] = useState<TableFilter>({});
  const [order, setOrder] = useState<SortOrder | null>(null);
  const [selectedRowKey, setSelectedRowKey] = useState<string | null>(null);
  const [openDialog, setOpenDialog] = useState<OpenDialog>(null);
  const [isStatisticsOpen, setIsStatisticsOpen] = useState(false);
  const [localMessage, setLocalMessage] = useState<{ text: string; serial: number } | null>(null);
  const [upload, setUpload] = useState<{ done: number; total: number } | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const dragDepth = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);
  const folderInput = useRef<HTMLInputElement>(null);
  const messageSerial = useRef(0);

  const report = useCallback((text: string) => {
    messageSerial.current += 1;
    const serial = messageSerial.current;
    setLocalMessage({ text, serial });
    window.setTimeout(
      () => setLocalMessage((current) => (current?.serial === serial ? null : current)),
      LOCAL_MESSAGE_MILLISECONDS,
    );
  }, []);

  const call = useCallback(
    async (action: () => Promise<unknown>) => {
      try {
        await action();
        return true;
      } catch (error) {
        report(errorMessage(error));
        return false;
      }
    },
    [report],
  );

  const runAction = useCallback(
    async (action: (isSkippingApproved: boolean) => Promise<ActionReply>): Promise<boolean> => {
      try {
        let reply = await action(false);
        if (reply.status === "needs_approval") {
          const isApproved = await dialogs.confirm({
            title: "Skip reference-only classes?",
            message: reply.message,
            confirmLabel: "Detect Without Them",
          });
          if (!isApproved) return false;
          reply = await action(true);
        }
        if (reply.status === "rejected") {
          report(reply.message);
          return false;
        }
        return reply.status === "done";
      } catch (error) {
        report(errorMessage(error));
        return false;
      }
    },
    [dialogs, report],
  );

  const thresholds: Thresholds = state?.thresholds ?? { default_minimum: 0, class_minimums: {} };
  const allRows = useMemo(() => buildRows(detections, thresholds), [detections, thresholds]);
  const filteredRows = useMemo(() => filterRows(allRows, filter), [allRows, filter]);
  const rows = useMemo(() => sortRows(filteredRows, order), [filteredRows, order]);
  const listed = useMemo(() => listedIndices(filteredRows), [filteredRows]);

  const currentPath = state?.current_image?.path ?? null;
  const currentDetections: Detection[] = useMemo(
    () => detections?.images.find((image) => image.path === currentPath)?.detections ?? [],
    [detections, currentPath],
  );
  const selectedRow = rows.find((row) => row.key === selectedRowKey) ?? null;
  const highlightedIndex =
    selectedRow?.kind === "detection" && selectedRow.imagePath === currentPath ? selectedRow.detection.index : null;
  const outdatedCount = detections?.images.filter((image) => image.outdated !== null).length ?? 0;
  const classColors = useMemo(
    () => Object.fromEntries((state?.classes ?? []).map((entry) => [entry.name, entry.color])),
    [state?.classes],
  );

  const navigate = useCallback(
    (step: number) => {
      if (state === null) return;
      const index = state.images.findIndex((image) => image.path === currentPath);
      const next = state.images[Math.min(state.images.length - 1, Math.max(0, index + step))];
      if (next !== undefined && next.path !== currentPath) {
        setSelectedRowKey(null);
        void call(() => api.selectImage(next.path));
      }
    },
    [state, currentPath, call],
  );

  const selectRow = (row: TableRow) => {
    setSelectedRowKey(row.key);
    if (row.imagePath !== currentPath) void call(() => api.selectImage(row.imagePath));
  };

  const setAccepted = (targets: TableRow[], isAccepted: boolean) => {
    const indices: Record<string, number[]> = {};
    for (const row of targets) {
      if (row.kind !== "detection") continue;
      (indices[row.imagePath] ??= []).push(row.detection.index);
    }
    void call(() => api.setAccepted(indices, isAccepted));
  };

  const uploadFiles = useCallback(
    async (files: DroppedFile[]) => {
      if (files.length === 0) {
        report("No images found in what was dropped.");
        return;
      }
      setUpload({ done: 0, total: files.length });
      try {
        for (let start = 0; start < files.length; start += UPLOAD_CHUNK_SIZE) {
          await api.upload(files.slice(start, start + UPLOAD_CHUNK_SIZE), start === 0);
          setUpload({ done: Math.min(files.length, start + UPLOAD_CHUNK_SIZE), total: files.length });
        }
      } catch (error) {
        report(`Upload failed: ${errorMessage(error)}`);
      } finally {
        setUpload(null);
      }
    },
    [report],
  );

  const detect = useCallback(() => void runAction(api.detect), [runAction]);
  const detectAll = useCallback(() => void runAction(api.detectAll), [runAction]);

  const exportResults = async (choice: ExportChoice): Promise<boolean> => {
    let listedPayload: Record<string, number[]> | null = null;
    if (choice.scope === "listed" && Object.keys(filter).length > 0) {
      listedPayload = {};
      for (const image of detections?.images ?? []) {
        listedPayload[image.path] = [...(listed.get(image.path) ?? [])];
      }
    }
    return runAction((isSkippingApproved) =>
      api.exportResults({
        ...choice,
        listed_indices: listedPayload,
        is_confidence_shown: display.isConfidenceShown,
        is_skipping_approved: isSkippingApproved,
      }),
    );
  };

  const saveCsv = async () => {
    try {
      const blob = await api.tableCsv(
        rows.flatMap((row) => (row.kind === "detection" ? [{ path: row.imagePath, index: row.detection.index }] : [])),
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "detections.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      report(errorMessage(error));
    }
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const isCommand = event.metaKey || event.ctrlKey;
      if (!isCommand || document.querySelector(".overlay") !== null) return;
      if (event.key === "Enter") {
        event.preventDefault();
        if (event.shiftKey) detectAll();
        else detect();
      } else if (event.key.toLowerCase() === "e") {
        event.preventDefault();
        setOpenDialog({ kind: "export" });
      } else if (event.key.toLowerCase() === "i") {
        event.preventDefault();
        setIsStatisticsOpen((isOpen) => !isOpen);
      } else if (event.key.toLowerCase() === "o" && !isTyping(event.target)) {
        event.preventDefault();
        setOpenDialog({ kind: "browse" });
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [detect, detectAll]);

  useEffect(() => {
    const onDragEnter = (event: DragEvent) => {
      if (!hasFiles(event.dataTransfer)) return;
      event.preventDefault();
      dragDepth.current += 1;
      setIsDragOver(true);
    };
    const onDragOver = (event: DragEvent) => {
      if (!hasFiles(event.dataTransfer)) return;
      event.preventDefault();
      if (event.dataTransfer !== null) event.dataTransfer.dropEffect = "copy";
    };
    const onDragLeave = () => {
      dragDepth.current = Math.max(0, dragDepth.current - 1);
      if (dragDepth.current === 0) setIsDragOver(false);
    };
    const onDrop = (event: DragEvent) => {
      dragDepth.current = 0;
      setIsDragOver(false);
      if (!hasFiles(event.dataTransfer) || event.dataTransfer === null) return;
      event.preventDefault();
      void imageFilesOf(event.dataTransfer).then(uploadFiles);
    };
    window.addEventListener("dragenter", onDragEnter);
    window.addEventListener("dragover", onDragOver);
    window.addEventListener("dragleave", onDragLeave);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onDragEnter);
      window.removeEventListener("dragover", onDragOver);
      window.removeEventListener("dragleave", onDragLeave);
      window.removeEventListener("drop", onDrop);
    };
  }, [uploadFiles]);

  const statusSerial = state?.status.serial;
  useEffect(() => {
    setLocalMessage(null);
  }, [statusSerial]);

  useEffect(() => {
    if (selectedRowKey !== null && !allRows.some((row) => row.key === selectedRowKey)) setSelectedRowKey(null);
  }, [allRows, selectedRowKey]);

  if (state === null) {
    return (
      <div className="empty-center" style={{ background: "var(--bg)", color: "var(--text-muted)" }}>
        {workspace.connection === "closed" ? "Cannot reach the OVD GUI server; retrying…" : "Connecting…"}
      </div>
    );
  }

  const toggleSection = (name: string) =>
    setLayout((current) => ({
      ...current,
      collapsedSections: current.collapsedSections.includes(name)
        ? current.collapsedSections.filter((entry) => entry !== name)
        : [...current.collapsedSections, name],
    }));
  const isCollapsed = (name: string) => layout.collapsedSections.includes(name);
  const currentIndex = state.images.findIndex((image) => image.path === currentPath);
  const referenceClass = openDialog?.kind === "reference" ? state.classes[openDialog.classIndex] : undefined;
  const displayEntries = [
    { key: "isLabelShown", label: "Labels" },
    { key: "isConfidenceShown", label: "Confidences" },
    { key: "isRejectedShown", label: "Rejected boxes" },
    { key: "isComparedShown", label: "Compared model" },
    { key: "isFilled", label: "Fill boxes" },
  ] as const;

  return (
    <div className="app">
      <div className="toolbar">
        <span className="title">OVD GUI</span>
        <button onClick={() => fileInput.current?.click()} title="Upload images from this computer">
          Upload Images…
        </button>
        <button onClick={() => folderInput.current?.click()} title="Upload a folder from this computer">
          Upload Folder…
        </button>
        <button onClick={() => setOpenDialog({ kind: "browse" })} title="Open images already on the server (Ctrl+O)">
          Open from Server…
        </button>
        <span className="separator" />
        <button className="icon" disabled={currentIndex <= 0} onClick={() => navigate(-1)} title="Previous image (←)">
          ◀
        </button>
        <button
          className="icon"
          disabled={currentIndex < 0 || currentIndex >= state.images.length - 1}
          onClick={() => navigate(1)}
          title="Next image (→)"
        >
          ▶
        </button>
        <span className="separator" />
        <button className="primary" disabled={state.is_busy} onClick={detect} title="Detect the shown image (Ctrl+Enter)">
          Detect
        </button>
        <button disabled={state.is_busy} onClick={detectAll} title="Detect every open image (Ctrl+Shift+Enter)">
          Detect All
        </button>
        <span className="separator" />
        <button disabled={state.is_busy} onClick={() => setOpenDialog({ kind: "export" })} title="Export annotations (Ctrl+E)">
          Export…
        </button>
        <button
          onClick={(event) =>
            menu.openBelow(event.currentTarget, [
              ...displayEntries.map((entry) => ({
                label: entry.label,
                isChecked: display[entry.key],
                isDisabled: entry.key === "isComparedShown" && state.compared_profile_key === null,
                onSelect: () => setDisplay((current) => ({ ...current, [entry.key]: !current[entry.key] })),
              })),
              { isSeparator: true, label: "" },
              ...[1, 2, 3, 4].map((width) => ({
                label: `Line width ${width}`,
                isChecked: display.lineWidth === width,
                onSelect: () => setDisplay((current) => ({ ...current, lineWidth: width })),
              })),
            ])
          }
        >
          View ▾
        </button>
        <button onClick={() => setIsStatisticsOpen((isOpen) => !isOpen)} title="Statistics and class minimums (Ctrl+I)">
          Statistics…
        </button>
        <span className="spacer" />
        <span className={`connection ${workspace.connection}`}>
          {workspace.connection === "open" ? "● connected" : workspace.connection === "closed" ? "● disconnected" : "● connecting"}
        </span>
      </div>

      <div className="main">
        <div className="sidebar" style={{ width: layout.sidebarWidth, flex: "none" }}>
          <Section title="Model" isCollapsed={isCollapsed("model")} onToggle={() => toggleSection("model")}>
            <ModelPanel
              model={state.model}
              isDisabled={state.is_busy}
              onSelectPreset={(backend, preset) => void call(() => api.selectPreset(backend, preset))}
              onChange={(selection: ModelSelection) => void call(() => api.selectModel(selection))}
            />
          </Section>
          <Section
            title={`Classes (${state.classes.length})`}
            isCollapsed={isCollapsed("classes")}
            onToggle={() => toggleSection("classes")}
            isStretched
          >
            <ClassEditor
              classes={state.classes}
              classSet={state.class_set}
              isImagePromptSupported={state.is_image_prompt_supported}
              onReport={report}
              onAddImagePrompt={(classIndex) => setOpenDialog({ kind: "reference", classIndex })}
              onOpenLibrary={() => setOpenDialog({ kind: "class-sets" })}
              onEditAsText={() => setOpenDialog({ kind: "class-text" })}
            />
          </Section>
          <Section
            title={`Images (${state.images.length})`}
            isCollapsed={isCollapsed("images")}
            onToggle={() => toggleSection("images")}
            isStretched
          >
            <ImageList
              images={state.images}
              currentPath={currentPath}
              backgroundPath={state.background_image_path}
              onSelect={(path) => {
                setSelectedRowKey(null);
                void call(() => api.selectImage(path));
              }}
              onClose={(paths) => void call(() => api.closeImages(paths))}
            />
          </Section>
        </div>
        <Splitter
          onResize={(delta) =>
            setLayout((current) => ({ ...current, sidebarWidth: Math.max(220, Math.min(640, current.sidebarWidth + delta)) }))
          }
        />
        <div className="center">
          <DetectionViewer
            image={state.current_image}
            detections={currentDetections}
            listedIndices={currentPath === null ? null : (listed.get(currentPath) ?? new Set())}
            highlightedIndex={highlightedIndex}
            options={display}
            palette={state.palette}
            isImageListEmpty={state.images.length === 0}
            onSelectDetection={(index) => currentPath !== null && setSelectedRowKey(`${currentPath}#${index}`)}
            onClearSelection={() => setSelectedRowKey(null)}
            onNavigate={navigate}
            onUploadRequested={() => fileInput.current?.click()}
            onBrowseRequested={() => setOpenDialog({ kind: "browse" })}
          />
        </div>
        <Splitter
          onResize={(delta) =>
            setLayout((current) => ({ ...current, rightWidth: Math.max(320, Math.min(1000, current.rightWidth - delta)) }))
          }
        />
        <div className="right-panel" style={{ width: layout.rightWidth, flex: "none" }}>
          <div style={{ height: layout.profileHeight, flex: "none", minHeight: 0 }}>
            <ProfileTable
              profiles={state.profiles}
              shownKey={state.shown_profile_key}
              comparedKey={state.compared_profile_key}
              onSelect={(key) => void call(() => api.selectProfile(key))}
              onRemove={(key) => void call(() => api.removeProfile(key))}
            />
          </div>
          <Splitter
            isHorizontal
            onResize={(delta) =>
              setLayout((current) => ({
                ...current,
                profileHeight: Math.max(90, Math.min(600, current.profileHeight + delta)),
              }))
            }
          />
          <div style={{ flex: 1, minHeight: 0, borderTop: "1px solid var(--border)" }}>
            <DetectionTable
              rows={rows}
              allRows={allRows}
              filter={filter}
              onFilterChange={setFilter}
              order={order}
              onOrderChange={setOrder}
              currentPath={currentPath}
              selectedKey={selectedRowKey}
              onSelectRow={selectRow}
              onSetAccepted={setAccepted}
              onSaveCsv={() => void saveCsv()}
              onUpdateOutdated={() => void runAction(api.updateOutdated)}
              onClearResults={() => void call(api.clearResults)}
              outdatedCount={outdatedCount}
              hasResults={state.profiles.length > 0}
              palette={state.palette}
            />
          </div>
        </div>
      </div>

      <StatusBar
        state={state}
        localMessage={localMessage?.text ?? null}
        upload={upload}
        onCancel={() => void call(api.cancel)}
      />

      {workspace.notices.length > 0 && (
        <div className="notices">
          {workspace.notices.map((notice) => (
            <div key={notice.id} className="notice">
              <div className="body">
                <div className="title">{notice.title}</div>
                {notice.message}
              </div>
              <button className="ghost icon" onClick={() => workspace.dismissNotice(notice.id)}>
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {isDragOver && (
        <div className="drop-overlay">
          <div className="card">
            <div style={{ fontWeight: 600 }}>Drop images or folders to upload and open them</div>
            <div className="hint">They are stored on the server in {state.upload_directory}</div>
          </div>
        </div>
      )}

      {isStatisticsOpen && (
        <StatisticsPanel
          refreshToken={`${state.status.serial}:${state.shown_profile_key}:${state.compared_profile_key}:${JSON.stringify(state.thresholds)}:${detections?.images.length ?? 0}:${allRows.length}`}
          thresholds={state.thresholds}
          classColors={classColors}
          profiles={state.profiles}
          shownKey={state.shown_profile_key}
          comparedKey={state.compared_profile_key}
          onThresholdsChange={(next) => void call(() => api.setThresholds(next.default_minimum, next.class_minimums))}
          onCompare={(key) => void call(() => api.compare(key))}
          onClose={() => setIsStatisticsOpen(false)}
        />
      )}

      {openDialog?.kind === "browse" && (
        <ServerBrowserDialog
          mode="images"
          title="Open Images from the Server"
          onChoose={(paths) => {
            setOpenDialog(null);
            void call(() => api.openPaths(paths));
          }}
          onClose={() => setOpenDialog(null)}
        />
      )}
      {openDialog?.kind === "export" && (
        <ExportDialog onExport={exportResults} onClose={() => setOpenDialog(null)} />
      )}
      {openDialog?.kind === "class-sets" && (
        <ClassSetDialog
          classSet={state.class_set}
          version={workspace.classSetsVersion}
          onReport={report}
          onClose={() => setOpenDialog(null)}
        />
      )}
      {openDialog?.kind === "class-text" && (
        <ClassTextDialog classes={state.classes} onClose={() => setOpenDialog(null)} />
      )}
      {openDialog?.kind === "reference" && referenceClass !== undefined && (
        <ReferenceDialog
          classIndex={openDialog.classIndex}
          classEntry={referenceClass}
          onAdded={() => undefined}
          onClose={() => setOpenDialog(null)}
        />
      )}

      <input
        ref={fileInput}
        type="file"
        accept="image/*,.tif,.tiff"
        multiple
        hidden
        onChange={(event) => {
          const files = imageFilesOfList(event.target.files);
          event.target.value = "";
          void uploadFiles(files);
        }}
      />
      <input
        ref={folderInput}
        type="file"
        multiple
        hidden
        {...{ webkitdirectory: "" }}
        onChange={(event) => {
          const files = imageFilesOfList(event.target.files);
          event.target.value = "";
          void uploadFiles(files);
        }}
      />
      {menu.element}
    </div>
  );
}
