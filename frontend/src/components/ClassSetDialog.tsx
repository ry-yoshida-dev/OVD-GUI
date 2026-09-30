import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { ClassSetListEntry, ClassSetPreview, ClassSetState } from "../api/types";
import { Dialog } from "./Dialog";
import { useDialogs } from "./DialogHost";

interface ClassSetDialogProps {
  classSet: ClassSetState;
  version: number;
  onReport: (message: string) => void;
  onClose: () => void;
}

export function ClassSetDialog({ classSet, version, onReport, onClose }: ClassSetDialogProps) {
  const dialogs = useDialogs();
  const [entries, setEntries] = useState<ClassSetListEntry[]>([]);
  const [search, setSearch] = useState("");
  const [selectedName, setSelectedName] = useState<string | null>(classSet.name || null);
  const [preview, setPreview] = useState<ClassSetPreview | null>(null);
  const [error, setError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .classSets()
      .then((loaded) => setEntries(loaded.entries))
      .catch((caught: unknown) => setError(errorMessage(caught)));
  }, [version]);

  useEffect(() => {
    setPreview(null);
    if (selectedName === null) return;
    let isCurrent = true;
    api
      .classSetPreview(selectedName)
      .then((loaded) => isCurrent && setPreview(loaded))
      .catch(() => isCurrent && setPreview(null));
    return () => {
      isCurrent = false;
    };
  }, [selectedName, version]);

  const needle = search.trim().toLowerCase();
  const shown = entries.filter(
    (entry) =>
      needle === "" ||
      entry.name.toLowerCase().includes(needle) ||
      entry.class_names.some((name) => name.toLowerCase().includes(needle)),
  );
  const selected = entries.find((entry) => entry.name === selectedName) ?? null;

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      setError("");
      onReport(message);
      return true;
    } catch (caught) {
      setError(errorMessage(caught));
      return false;
    }
  };

  const load = async () => {
    if (selected === null) return;
    if (classSet.is_unsaved) {
      const isConfirmed = await dialogs.confirm({
        title: "Load Class Set",
        message: `Load '${selected.name}' and discard the current unsaved classes?`,
        confirmLabel: "Discard and Load",
        isDanger: true,
      });
      if (!isConfirmed) return;
    }
    if (await run(() => api.loadClassSet(selected.name), `Loaded the class set '${selected.name}'.`)) onClose();
  };

  const rename = async () => {
    if (selected === null) return;
    const name = await dialogs.prompt({ title: "Rename Class Set", label: "New name", initialValue: selected.name });
    if (name === null || name === selected.name) return;
    if (await run(() => api.renameClassSet(selected.name, name), `Renamed '${selected.name}' to '${name}'.`)) {
      setSelectedName(name);
    }
  };

  const remove = async () => {
    if (selected === null) return;
    const isConfirmed = await dialogs.confirm({
      title: "Delete Class Set",
      message: `Delete the class set '${selected.name}'? This cannot be undone.`,
      confirmLabel: "Delete",
      isDanger: true,
    });
    if (isConfirmed && (await run(() => api.deleteClassSet(selected.name), `Deleted '${selected.name}'.`))) {
      setSelectedName(null);
    }
  };

  return (
    <Dialog
      title="Class Sets"
      onClose={onClose}
      width={820}
      height={560}
      footer={
        <>
          <div className="left row">
            <button onClick={() => fileInput.current?.click()}>Import…</button>
            {selected !== null && (
              <a href={api.classSetFileUrl(selected.name)} download>
                <button>Export…</button>
              </a>
            )}
          </div>
          <button onClick={onClose}>Close</button>
          <button className="primary" disabled={selected === null || !selected.is_readable} onClick={() => void load()}>
            Load
          </button>
        </>
      }
    >
      {error !== "" && <div className="error-text">{error}</div>}
      <div className="split-view" style={{ flex: 1 }}>
        <div style={{ width: 300, display: "flex", flexDirection: "column", gap: 6, minHeight: 0 }}>
          <input type="search" placeholder="Search sets and classes" value={search} onChange={(event) => setSearch(event.target.value)} />
          <div
            className="list"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Delete" || event.key === "Backspace") void remove();
              if (event.key === "F2") void rename();
              if (event.key === "Enter") void load();
            }}
          >
            {shown.length === 0 && <div className="list-item faint">No class sets.</div>}
            {shown.map((entry) => (
              <div
                key={entry.name}
                className={`list-item${entry.name === selectedName ? " selected" : ""}`}
                style={{ flexDirection: "column", alignItems: "stretch", padding: "5px 8px" }}
                onClick={() => setSelectedName(entry.name)}
                onDoubleClick={() => void load()}
              >
                <div className="row">
                  <b className="grow">{entry.name}</b>
                  {entry.name === classSet.name && <span className="badge">current</span>}
                </div>
                <div className="small muted" style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                  {entry.is_readable ? entry.description : "Unreadable file"} · {new Date(entry.saved_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
          <div className="row">
            <b className="grow">{selected?.name ?? "Select a class set"}</b>
            <button disabled={selected === null} onClick={() => void rename()}>
              Rename
            </button>
            <button className="danger" disabled={selected === null} onClick={() => void remove()}>
              Delete
            </button>
          </div>
          <div className="list" style={{ padding: 6 }}>
            {preview?.classes.map((entry) => (
              <div key={entry.name} style={{ marginBottom: 8 }}>
                <div className="row">
                  <span className="swatch" style={{ background: entry.color }} />
                  <b>{entry.name}</b>
                  <span className="muted small">{entry.phrases.join(", ")}</span>
                </div>
                {entry.references.length > 0 && (
                  <div className="row wrap" style={{ marginTop: 4, marginLeft: 17 }}>
                    {entry.references.map((reference) => (
                      <img
                        key={reference.digest}
                        className="thumb"
                        style={{ width: 64, height: 48 }}
                        title={`${reference.name} · ${reference.boxes.length} boxes`}
                        src={api.classSetImageUrl(preview.name, reference.name, reference.digest)}
                        alt={reference.name}
                      />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
      <input
        ref={fileInput}
        type="file"
        accept=".ovdset"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file !== undefined) void run(() => api.importClassSet(file), `Imported ${file.name}.`);
        }}
      />
    </Dialog>
  );
}
