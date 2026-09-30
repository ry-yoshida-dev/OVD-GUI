import { type ReactNode, useEffect, useId } from "react";

const openDialogs: string[] = [];

interface DialogProps {
  title: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  width?: number | string;
  height?: number | string;
  isModal?: boolean;
}

export function Dialog({ title, onClose, children, footer, width, height, isModal = true }: DialogProps) {
  const id = useId();
  useEffect(() => {
    openDialogs.push(id);
    return () => {
      openDialogs.splice(openDialogs.indexOf(id), 1);
    };
  }, [id]);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && openDialogs[openDialogs.length - 1] === id) {
        event.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, id]);

  return (
    <div
      className="overlay"
      style={isModal ? undefined : { background: "transparent", pointerEvents: "none" }}
      onMouseDown={(event) => {
        if (isModal && event.target === event.currentTarget) onClose();
      }}
      onDragEnter={(event) => event.stopPropagation()}
      onDragOver={(event) => {
        event.stopPropagation();
        event.preventDefault();
        event.dataTransfer.dropEffect = "none";
      }}
      onDrop={(event) => {
        event.stopPropagation();
        event.preventDefault();
      }}
    >
      <div className="dialog" style={{ width, height, pointerEvents: "auto" }} role="dialog">
        <div className="dialog-header">
          <span className="grow">{title}</span>
          <button className="ghost icon" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="dialog-body" style={{ flex: height === undefined ? undefined : 1 }}>
          {children}
        </div>
        {footer !== undefined && <div className="dialog-footer">{footer}</div>}
      </div>
    </div>
  );
}
