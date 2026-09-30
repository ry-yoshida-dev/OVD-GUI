import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";
import { Dialog } from "./Dialog";

interface ConfirmOptions {
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  isDanger?: boolean;
}

interface PromptOptions {
  title: string;
  label: string;
  initialValue?: string;
  confirmLabel?: string;
  hint?: ReactNode;
}

interface Dialogs {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
  prompt: (options: PromptOptions) => Promise<string | null>;
}

type PendingDialog =
  | { kind: "confirm"; options: ConfirmOptions; resolve: (value: boolean) => void }
  | { kind: "prompt"; options: PromptOptions; resolve: (value: string | null) => void };

const DialogContext = createContext<Dialogs | null>(null);

export function useDialogs(): Dialogs {
  const dialogs = useContext(DialogContext);
  if (dialogs === null) throw new Error("useDialogs needs a DialogHost");
  return dialogs;
}

function PromptDialog({
  options,
  onDone,
}: {
  options: PromptOptions;
  onDone: (value: string | null) => void;
}) {
  const [value, setValue] = useState(options.initialValue ?? "");
  return (
    <Dialog
      title={options.title}
      onClose={() => onDone(null)}
      width={420}
      footer={
        <>
          <button onClick={() => onDone(null)}>Cancel</button>
          <button className="primary" disabled={value.trim() === ""} onClick={() => onDone(value.trim())}>
            {options.confirmLabel ?? "OK"}
          </button>
        </>
      }
    >
      <label style={{ flexDirection: "column", alignItems: "stretch" }}>
        <span className="muted">{options.label}</span>
        <input
          type="text"
          autoFocus
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && value.trim() !== "") onDone(value.trim());
          }}
        />
      </label>
      {options.hint !== undefined && <div className="hint">{options.hint}</div>}
    </Dialog>
  );
}

export function DialogHost({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState<PendingDialog | null>(null);

  const confirm = useCallback(
    (options: ConfirmOptions) =>
      new Promise<boolean>((resolve) => setPending({ kind: "confirm", options, resolve })),
    [],
  );
  const prompt = useCallback(
    (options: PromptOptions) =>
      new Promise<string | null>((resolve) => setPending({ kind: "prompt", options, resolve })),
    [],
  );
  const dialogs = useMemo(() => ({ confirm, prompt }), [confirm, prompt]);

  let element: ReactNode = null;
  if (pending?.kind === "confirm") {
    const done = (value: boolean) => {
      setPending(null);
      pending.resolve(value);
    };
    element = (
      <Dialog
        title={pending.options.title}
        onClose={() => done(false)}
        width={440}
        footer={
          <>
            <button onClick={() => done(false)}>Cancel</button>
            <button
              className={pending.options.isDanger ? "primary danger" : "primary"}
              style={pending.options.isDanger ? { background: "var(--danger)", borderColor: "var(--danger)" } : {}}
              autoFocus
              onClick={() => done(true)}
            >
              {pending.options.confirmLabel ?? "OK"}
            </button>
          </>
        }
      >
        <div style={{ whiteSpace: "pre-wrap" }}>{pending.options.message}</div>
      </Dialog>
    );
  } else if (pending?.kind === "prompt") {
    element = (
      <PromptDialog
        options={pending.options}
        onDone={(value) => {
          setPending(null);
          pending.resolve(value);
        }}
      />
    );
  }

  return (
    <DialogContext.Provider value={dialogs}>
      {children}
      {element}
    </DialogContext.Provider>
  );
}
