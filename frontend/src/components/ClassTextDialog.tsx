import { useState } from "react";
import { api, errorMessage } from "../api/client";
import type { ClassEntry } from "../api/types";
import { Dialog } from "./Dialog";

interface ClassTextDialogProps {
  classes: ClassEntry[];
  onClose: () => void;
}

function textOf(entry: ClassEntry): string {
  if (entry.phrases.length === 1 && entry.phrases[0] === entry.name) return entry.name;
  return `${entry.name}: ${entry.phrases.join(", ")}`.trimEnd();
}

export function ClassTextDialog({ classes, onClose }: ClassTextDialogProps) {
  const [text, setText] = useState(() => classes.map(textOf).join("\n"));
  const [error, setError] = useState("");
  const apply = async () => {
    try {
      await api.replaceClassesText(text);
      onClose();
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };
  return (
    <Dialog
      title="Edit Classes as Text"
      onClose={onClose}
      width={560}
      footer={
        <>
          <button onClick={onClose}>Cancel</button>
          <button className="primary" onClick={() => void apply()}>
            Apply
          </button>
        </>
      }
    >
      <div className="hint">
        One class per line: <span className="mono">person</span> or <span className="mono">car: car, suv, taxi</span>.
        Reference images stay with the classes that keep their name.
      </div>
      <textarea
        className="mono"
        rows={16}
        value={text}
        autoFocus
        spellCheck={false}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) void apply();
        }}
      />
      {error !== "" && <div className="error-text">{error}</div>}
    </Dialog>
  );
}
