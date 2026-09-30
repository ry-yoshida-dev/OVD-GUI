import { useEffect, useMemo, useRef, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { ClassEntry, ClassSetState, ReferenceEntry } from "../api/types";
import { useDialogs } from "./DialogHost";
import { useMenu } from "./Menu";

interface ClassEditorProps {
  classes: ClassEntry[];
  classSet: ClassSetState;
  isImagePromptSupported: boolean;
  onReport: (message: string) => void;
  onAddImagePrompt: (classIndex: number) => void;
  onOpenLibrary: () => void;
  onEditAsText: () => void;
}

type RowKey = string;

type Editing =
  | { kind: "rename-class"; classIndex: number }
  | { kind: "rename-phrase"; classIndex: number; phraseIndex: number }
  | { kind: "new-class"; position: number }
  | { kind: "new-phrase"; classIndex: number; position: number };

type DragPayload =
  | { kind: "phrase"; classIndex: number; phraseIndex: number }
  | { kind: "reference"; classIndex: number; name: string; digest: string };

type DropTarget =
  | { kind: "into-class"; classIndex: number }
  | { kind: "before-class"; classIndex: number }
  | { kind: "before-phrase"; classIndex: number; phraseIndex: number }
  | { kind: "end" };

const DRAG_TYPE = "application/x-ovd-query";

const classKey = (classIndex: number): RowKey => `c:${classIndex}`;
const phraseKey = (classIndex: number, phraseIndex: number): RowKey => `p:${classIndex}:${phraseIndex}`;
const referenceKey = (classIndex: number, reference: ReferenceEntry): RowKey =>
  `r:${classIndex}:${reference.digest}:${reference.name}`;

function parseKey(key: RowKey) {
  const [kind, first, ...rest] = key.split(":");
  const classIndex = Number(first);
  switch (kind) {
    case "c":
      return { kind: "class" as const, classIndex };
    case "p":
      return { kind: "phrase" as const, classIndex, phraseIndex: Number(rest[0]) };
    default:
      return { kind: "reference" as const, classIndex, digest: rest[0] ?? "", name: rest.slice(1).join(":") };
  }
}

function InlineInput({
  initialValue,
  placeholder,
  onCommit,
  onCancel,
}: {
  initialValue: string;
  placeholder: string;
  onCommit: (value: string) => Promise<boolean>;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(initialValue);
  const isCommitting = useRef(false);
  const commit = async () => {
    if (isCommitting.current) return;
    if (value.trim() === "" || value === initialValue) {
      onCancel();
      return;
    }
    isCommitting.current = true;
    const isDone = await onCommit(value);
    isCommitting.current = false;
    if (!isDone) setValue(value);
  };
  return (
    <input
      type="text"
      autoFocus
      value={value}
      placeholder={placeholder}
      onChange={(event) => setValue(event.target.value)}
      onClick={(event) => event.stopPropagation()}
      onDoubleClick={(event) => event.stopPropagation()}
      onKeyDown={(event) => {
        event.stopPropagation();
        if (event.key === "Enter") void commit();
        if (event.key === "Escape") onCancel();
      }}
      onBlur={() => void commit()}
    />
  );
}

export function ClassEditor({
  classes,
  classSet,
  isImagePromptSupported,
  onReport,
  onAddImagePrompt,
  onOpenLibrary,
  onEditAsText,
}: ClassEditorProps) {
  const dialogs = useDialogs();
  const menu = useMenu();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<RowKey | null>(null);
  const [editing, setEditing] = useState<Editing | null>(null);
  const [dropTarget, setDropTarget] = useState<DropTarget | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const treeElement = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selected === null) return;
    const parsed = parseKey(selected);
    const entry = classes[parsed.classIndex];
    const isValid =
      entry !== undefined &&
      (parsed.kind === "class" ||
        (parsed.kind === "phrase" && parsed.phraseIndex < entry.phrases.length) ||
        (parsed.kind === "reference" && entry.references.some((reference) => reference.digest === parsed.digest)));
    if (!isValid) setSelected(null);
  }, [classes, selected]);

  const selectedClassIndex = selected === null ? null : parseKey(selected).classIndex;

  const run = async (action: () => Promise<unknown>): Promise<boolean> => {
    try {
      await action();
      return true;
    } catch (error) {
      onReport(errorMessage(error));
      return false;
    }
  };

  const expand = (name: string) => setExpanded((current) => new Set(current).add(name));

  const startNewRow = () => {
    if (selected === null) {
      setEditing({ kind: "new-class", position: classes.length });
      return;
    }
    const parsed = parseKey(selected);
    const entry = classes[parsed.classIndex];
    if (entry === undefined) return;
    switch (parsed.kind) {
      case "class":
        setEditing({ kind: "new-class", position: parsed.classIndex + 1 });
        break;
      case "phrase":
        setEditing({ kind: "new-phrase", classIndex: parsed.classIndex, position: parsed.phraseIndex + 1 });
        break;
      case "reference":
        expand(entry.name);
        setEditing({ kind: "new-phrase", classIndex: parsed.classIndex, position: entry.phrases.length });
        break;
    }
  };

  const removeSelection = async () => {
    if (selected === null) return;
    const parsed = parseKey(selected);
    const body = {
      class_indices: parsed.kind === "class" ? [parsed.classIndex] : [],
      phrases: parsed.kind === "phrase" ? [{ class_index: parsed.classIndex, phrase_index: parsed.phraseIndex }] : [],
      references:
        parsed.kind === "reference"
          ? [{ class_index: parsed.classIndex, name: parsed.name, digest: parsed.digest }]
          : [],
    };
    if (await run(() => api.removeClassRows(body))) setSelected(null);
  };

  const commitEditing = async (value: string): Promise<boolean> => {
    if (editing === null) return true;
    let isDone = false;
    switch (editing.kind) {
      case "rename-class":
        isDone = await run(() => api.renameClass(editing.classIndex, value));
        break;
      case "rename-phrase":
        isDone = await run(() => api.renamePhrase(editing.classIndex, editing.phraseIndex, value));
        break;
      case "new-class":
        isDone = await run(() => api.addClassRow(value, null, editing.position));
        if (isDone) {
          if (value.includes(":")) expand(value.split(":")[0]?.trim() ?? "");
          setSelected(classKey(Math.min(editing.position, classes.length)));
        }
        break;
      case "new-phrase": {
        isDone = await run(() => api.addClassRow(value, editing.classIndex, editing.position));
        const entry = classes[editing.classIndex];
        if (isDone && entry !== undefined) {
          expand(entry.name);
          setSelected(phraseKey(editing.classIndex, editing.position));
        }
        break;
      }
    }
    if (isDone) {
      setEditing(null);
      treeElement.current?.focus();
    }
    return isDone;
  };

  const onDragStart = (event: React.DragEvent, payload: DragPayload) => {
    event.dataTransfer.setData(DRAG_TYPE, JSON.stringify(payload));
    event.dataTransfer.effectAllowed = "move";
  };

  const acceptsDrag = (event: React.DragEvent) => event.dataTransfer.types.includes(DRAG_TYPE);

  const onDragOver = (event: React.DragEvent, target: DropTarget) => {
    if (!acceptsDrag(event)) return;
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = "move";
    setDropTarget(target);
  };

  const onDrop = async (event: React.DragEvent) => {
    const target = dropTarget;
    setDropTarget(null);
    if (!acceptsDrag(event) || target === null) return;
    event.preventDefault();
    event.stopPropagation();
    const payload = JSON.parse(event.dataTransfer.getData(DRAG_TYPE)) as DragPayload;
    if (payload.kind === "reference") {
      const targetClassIndex = target.kind === "end" ? null : target.classIndex;
      if (targetClassIndex !== null && targetClassIndex !== payload.classIndex) {
        await run(() => api.moveReference(payload.classIndex, payload.name, payload.digest, targetClassIndex));
      }
      return;
    }
    switch (target.kind) {
      case "into-class": {
        const entry = classes[target.classIndex];
        if (entry === undefined || target.classIndex === payload.classIndex) return;
        await run(() => api.movePhrase(payload.classIndex, payload.phraseIndex, target.classIndex, entry.phrases.length));
        expand(entry.name);
        break;
      }
      case "before-phrase":
        await run(() => api.movePhrase(payload.classIndex, payload.phraseIndex, target.classIndex, target.phraseIndex));
        break;
      case "before-class":
        await run(() => api.movePhrase(payload.classIndex, payload.phraseIndex, null, target.classIndex));
        break;
      case "end":
        await run(() => api.movePhrase(payload.classIndex, payload.phraseIndex, null, classes.length));
        break;
    }
  };

  const chooseClassSet = async (name: string) => {
    if (name === "" || (name === classSet.name && !classSet.is_edited)) return;
    if (classSet.is_unsaved) {
      const described = classSet.name === "" ? "the current unsaved classes" : `the unsaved edits to '${classSet.name}'`;
      const isConfirmed = await dialogs.confirm({
        title: "Load Class Set",
        message: `Load the class set '${name}' and discard ${described}?`,
        confirmLabel: "Discard and Load",
        isDanger: true,
      });
      if (!isConfirmed) return;
    }
    if (await run(() => api.loadClassSet(name))) onReport(`Loaded the class set '${name}'.`);
  };

  const saveClassSet = async () => {
    const name = await dialogs.prompt({
      title: "Save Class Set",
      label: "Set name",
      initialValue: classSet.name,
      confirmLabel: "Save",
      hint: `Saved with the phrases and reference images in ${classSet.directory}.`,
    });
    if (name === null) return;
    if (classSet.names.includes(name) && name !== classSet.name) {
      const isConfirmed = await dialogs.confirm({
        title: "Replace Class Set",
        message: `A class set named '${name}' exists. Replace it?`,
        confirmLabel: "Replace",
        isDanger: true,
      });
      if (!isConfirmed) return;
    }
    if (await run(() => api.saveClassSet(name))) onReport(`Saved the class set '${name}'.`);
  };

  const clearAll = async () => {
    const isConfirmed = await dialogs.confirm({
      title: "Clear All Classes",
      message: `Remove all ${classes.length} classes with their prompts and reference images?`,
      confirmLabel: "Clear",
      isDanger: true,
    });
    if (isConfirmed) await run(api.clearClasses);
  };

  const rows = useMemo(() => classes.map((entry, classIndex) => ({ entry, classIndex })), [classes]);

  const renderEditing = (placeholder: string, initialValue = "") => (
    <InlineInput
      initialValue={initialValue}
      placeholder={placeholder}
      onCommit={commitEditing}
      onCancel={() => {
        setEditing(null);
        treeElement.current?.focus();
      }}
    />
  );

  const newClassRow = (position: number) =>
    editing?.kind === "new-class" && editing.position === position ? (
      <div className="tree-row">
        <span className="toggle" />
        <span className="swatch" style={{ background: "var(--border-strong)" }} />
        {renderEditing("class or class: phrase, phrase")}
      </div>
    ) : null;

  return (
    <>
      <div className="row">
        <select
          className="grow"
          value={classSet.names.includes(classSet.name) ? classSet.name : ""}
          disabled={classSet.names.length === 0}
          title={
            classSet.names.length === 0
              ? "No class set saved yet; save the classes to list them here."
              : `Class sets saved in ${classSet.directory}; choose one to load it.`
          }
          onChange={(event) => void chooseClassSet(event.target.value)}
        >
          <option value="" disabled>
            {classSet.names.length === 0 ? "No saved sets" : "Choose a class set…"}
          </option>
          {classSet.names.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        {classSet.name !== "" && classSet.is_edited && <span className="badge warning">Edited</span>}
        <button onClick={() => void saveClassSet()} disabled={classes.length === 0}>
          Save…
        </button>
      </div>
      <div className="row">
        <button onClick={startNewRow} title="Add a class, or a phrase next to the selected phrase">
          + Text
        </button>
        <button
          onClick={() => selectedClassIndex !== null && onAddImagePrompt(selectedClassIndex)}
          disabled={selectedClassIndex === null || !isImagePromptSupported}
          title={
            isImagePromptSupported
              ? "Add example images to the selected class"
              : "Image prompts need OWL-ViT or YOLOE"
          }
        >
          + Image
        </button>
        <span className="grow" />
        <button className="ghost icon" onClick={() => void removeSelection()} disabled={selected === null} title="Remove (Delete)">
          🗑
        </button>
        <button
          className="ghost icon"
          title="More"
          onClick={(event) =>
            menu.openBelow(event.currentTarget, [
              { label: "Class Sets…", onSelect: onOpenLibrary },
              { label: "Edit as Text…", onSelect: onEditAsText },
              { label: "Open File…", onSelect: () => fileInput.current?.click() },
              { isSeparator: true, label: "" },
              { label: "Clear All…", onSelect: () => void clearAll(), isDisabled: classes.length === 0 },
            ])
          }
        >
          ⋯
        </button>
      </div>
      <div
        ref={treeElement}
        className="list"
        tabIndex={0}
        style={{ display: "flex", flexDirection: "column", paddingBottom: 4 }}
        onKeyDown={(event) => {
          if (editing !== null) return;
          if (event.key === "Delete" || event.key === "Backspace") {
            event.preventDefault();
            void removeSelection();
          } else if (event.key === "F2" && selected !== null) {
            const parsed = parseKey(selected);
            if (parsed.kind === "class") setEditing({ kind: "rename-class", classIndex: parsed.classIndex });
            if (parsed.kind === "phrase") {
              setEditing({ kind: "rename-phrase", classIndex: parsed.classIndex, phraseIndex: parsed.phraseIndex });
            }
          } else if (event.key === "Enter" && selected === null) {
            startNewRow();
          }
        }}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDropTarget(null);
        }}
        onDrop={(event) => void onDrop(event)}
      >
        {rows.map(({ entry, classIndex }) => {
          const isExpanded = expanded.has(entry.name);
          const hasChildren = entry.phrases.length > 0 || entry.references.length > 0;
          const isReferenceOnly = entry.phrases.length === 0 && entry.references.length > 0;
          return (
            <div key={`${classIndex}:${entry.name}`}>
              {newClassRow(classIndex)}
              <div
                className={[
                  "tree-row",
                  selected === classKey(classIndex) ? "selected" : "",
                  dropTarget?.kind === "into-class" && dropTarget.classIndex === classIndex ? "drop-into" : "",
                  dropTarget?.kind === "before-class" && dropTarget.classIndex === classIndex ? "drop-before" : "",
                  isReferenceOnly && !isImagePromptSupported ? "disabled" : "",
                ].join(" ")}
                onClick={() => setSelected(classKey(classIndex))}
                onDoubleClick={() => setEditing({ kind: "rename-class", classIndex })}
                onContextMenu={(event) => {
                  event.preventDefault();
                  setSelected(classKey(classIndex));
                  menu.open(event.clientX, event.clientY, [
                    { label: "Rename", shortcut: "F2", onSelect: () => setEditing({ kind: "rename-class", classIndex }) },
                    {
                      label: "New Phrase",
                      onSelect: () => {
                        expand(entry.name);
                        setEditing({ kind: "new-phrase", classIndex, position: entry.phrases.length });
                      },
                    },
                    {
                      label: "Add Image Prompt…",
                      isDisabled: !isImagePromptSupported,
                      onSelect: () => onAddImagePrompt(classIndex),
                    },
                    { label: "New Class Below", onSelect: () => setEditing({ kind: "new-class", position: classIndex + 1 }) },
                    { isSeparator: true, label: "" },
                    {
                      label: "Remove Class",
                      shortcut: "Del",
                      onSelect: () =>
                        void run(() => api.removeClassRows({ class_indices: [classIndex], phrases: [], references: [] })),
                    },
                  ]);
                }}
                onDragOver={(event) => {
                  const bounds = event.currentTarget.getBoundingClientRect();
                  const isUpper = event.clientY - bounds.top < bounds.height * 0.3;
                  onDragOver(event, isUpper ? { kind: "before-class", classIndex } : { kind: "into-class", classIndex });
                }}
              >
                <span
                  className="toggle"
                  onClick={(event) => {
                    event.stopPropagation();
                    setExpanded((current) => {
                      const next = new Set(current);
                      if (next.has(entry.name)) next.delete(entry.name);
                      else next.add(entry.name);
                      return next;
                    });
                  }}
                >
                  {hasChildren ? (isExpanded ? "▾" : "▸") : ""}
                </span>
                <span className="swatch" style={{ background: entry.color }} />
                {editing?.kind === "rename-class" && editing.classIndex === classIndex ? (
                  renderEditing("class name", entry.name)
                ) : (
                  <>
                    <span className="label" title={entry.phrases.join(", ")}>
                      {entry.name}
                    </span>
                    <span className="faint small">
                      {[
                        entry.phrases.length === 1 && entry.phrases[0] === entry.name
                          ? ""
                          : `${entry.phrases.length} phrase${entry.phrases.length === 1 ? "" : "s"}`,
                        entry.references.length > 0
                          ? `${entry.references.length} image${entry.references.length === 1 ? "" : "s"}`
                          : "",
                      ]
                        .filter((part) => part !== "")
                        .join(" · ")}
                    </span>
                  </>
                )}
              </div>
              {isExpanded &&
                entry.phrases.map((phrase, phraseIndex) => (
                  <div key={`p-${phrase}`}>
                    {editing?.kind === "new-phrase" &&
                      editing.classIndex === classIndex &&
                      editing.position === phraseIndex && (
                        <div className="tree-row child">{renderEditing("phrase, phrase")}</div>
                      )}
                    <div
                      className={[
                        "tree-row child",
                        selected === phraseKey(classIndex, phraseIndex) ? "selected" : "",
                        dropTarget?.kind === "before-phrase" &&
                        dropTarget.classIndex === classIndex &&
                        dropTarget.phraseIndex === phraseIndex
                          ? "drop-before"
                          : "",
                      ].join(" ")}
                      draggable={editing === null}
                      onDragStart={(event) => onDragStart(event, { kind: "phrase", classIndex, phraseIndex })}
                      onDragEnd={() => setDropTarget(null)}
                      onDragOver={(event) => onDragOver(event, { kind: "before-phrase", classIndex, phraseIndex })}
                      onClick={() => setSelected(phraseKey(classIndex, phraseIndex))}
                      onDoubleClick={() => setEditing({ kind: "rename-phrase", classIndex, phraseIndex })}
                      onContextMenu={(event) => {
                        event.preventDefault();
                        setSelected(phraseKey(classIndex, phraseIndex));
                        menu.open(event.clientX, event.clientY, [
                          {
                            label: "Rename",
                            shortcut: "F2",
                            onSelect: () => setEditing({ kind: "rename-phrase", classIndex, phraseIndex }),
                          },
                          {
                            label: "New Phrase Below",
                            onSelect: () => setEditing({ kind: "new-phrase", classIndex, position: phraseIndex + 1 }),
                          },
                          {
                            label: "Make a Class of Its Own",
                            onSelect: () => void run(() => api.movePhrase(classIndex, phraseIndex, null, classIndex + 1)),
                          },
                          { isSeparator: true, label: "" },
                          {
                            label: "Remove Phrase",
                            shortcut: "Del",
                            onSelect: () =>
                              void run(() =>
                                api.removeClassRows({
                                  class_indices: [],
                                  phrases: [{ class_index: classIndex, phrase_index: phraseIndex }],
                                  references: [],
                                }),
                              ),
                          },
                        ]);
                      }}
                    >
                      <span className="faint">“</span>
                      {editing?.kind === "rename-phrase" &&
                      editing.classIndex === classIndex &&
                      editing.phraseIndex === phraseIndex ? (
                        renderEditing("phrase", phrase)
                      ) : (
                        <span className="label">{phrase}</span>
                      )}
                    </div>
                  </div>
                ))}
              {editing?.kind === "new-phrase" &&
                editing.classIndex === classIndex &&
                editing.position >= entry.phrases.length && (
                  <div className="tree-row child">{renderEditing("phrase, phrase")}</div>
                )}
              {isExpanded &&
                entry.references.map((reference) => (
                  <div
                    key={`r-${reference.digest}-${reference.name}`}
                    className={[
                      "tree-row child",
                      selected === referenceKey(classIndex, reference) ? "selected" : "",
                      isImagePromptSupported ? "" : "disabled",
                    ].join(" ")}
                    title={
                      isImagePromptSupported
                        ? `${reference.boxes.length} boxes on ${reference.name}`
                        : "The selected model does not take image prompts"
                    }
                    draggable
                    onDragStart={(event) =>
                      onDragStart(event, {
                        kind: "reference",
                        classIndex,
                        name: reference.name,
                        digest: reference.digest,
                      })
                    }
                    onDragEnd={() => setDropTarget(null)}
                    onDragOver={(event) => onDragOver(event, { kind: "into-class", classIndex })}
                    onClick={() => setSelected(referenceKey(classIndex, reference))}
                  >
                    <img className="thumb" src={api.referenceImageUrl(reference.name, reference.digest)} alt="" />
                    <span className="label">{reference.name}</span>
                    <span className="faint small">
                      {reference.boxes.length} box{reference.boxes.length === 1 ? "" : "es"}
                    </span>
                  </div>
                ))}
            </div>
          );
        })}
        {newClassRow(classes.length)}
        <div
          className={`tree-drop-end${dropTarget?.kind === "end" ? " drop-before" : ""}`}
          onDragOver={(event) => onDragOver(event, { kind: "end" })}
          onClick={() => setSelected(null)}
          onDoubleClick={() => setEditing({ kind: "new-class", position: classes.length })}
          title="Double-click to add a class"
        />
      </div>
      <div className="hint">
        Double-click to rename or add a class. Write <span className="mono">car: car, suv</span> to query a class by
        several phrases; drag phrases between classes.
      </div>
      <input
        ref={fileInput}
        type="file"
        accept=".ovdset,.txt,.names"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file !== undefined) void run(() => api.loadClassFile(file));
        }}
      />
      {menu.element}
    </>
  );
}
