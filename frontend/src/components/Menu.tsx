import { type ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";

export interface MenuEntry {
  label: ReactNode;
  onSelect?: () => void;
  isDisabled?: boolean;
  isChecked?: boolean;
  shortcut?: string;
  isSeparator?: boolean;
}

interface MenuProps {
  x: number;
  y: number;
  entries: MenuEntry[];
  onClose: () => void;
}

export function Menu({ x, y, entries, onClose }: MenuProps) {
  const reference = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ left: x, top: y });

  useLayoutEffect(() => {
    const element = reference.current;
    if (element === null) return;
    const bounds = element.getBoundingClientRect();
    setPosition({
      left: Math.max(4, Math.min(x, window.innerWidth - bounds.width - 4)),
      top: Math.max(4, Math.min(y, window.innerHeight - bounds.height - 4)),
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
    window.addEventListener("blur", onClose);
    return () => {
      window.removeEventListener("mousedown", onPointerDown, true);
      window.removeEventListener("keydown", onKeyDown, true);
      window.removeEventListener("blur", onClose);
    };
  }, [onClose]);

  return (
    <div className="menu" ref={reference} style={position} onContextMenu={(event) => event.preventDefault()}>
      {entries.map((entry, index) =>
        entry.isSeparator ? (
          <div key={index} className="menu-separator" />
        ) : (
          <div
            key={index}
            className={`menu-item${entry.isDisabled ? " disabled" : ""}`}
            onClick={() => {
              onClose();
              entry.onSelect?.();
            }}
          >
            <span style={{ width: 12 }}>{entry.isChecked ? "✓" : ""}</span>
            <span>{entry.label}</span>
            {entry.shortcut !== undefined && <span className="shortcut">{entry.shortcut}</span>}
          </div>
        ),
      )}
    </div>
  );
}

export function useMenu() {
  const [menu, setMenu] = useState<{ x: number; y: number; entries: MenuEntry[] } | null>(null);
  const element =
    menu === null ? null : <Menu x={menu.x} y={menu.y} entries={menu.entries} onClose={() => setMenu(null)} />;
  const open = (x: number, y: number, entries: MenuEntry[]) => setMenu({ x, y, entries });
  const openBelow = (target: HTMLElement, entries: MenuEntry[]) => {
    const bounds = target.getBoundingClientRect();
    setMenu({ x: bounds.left, y: bounds.bottom + 2, entries });
  };
  return { element, open, openBelow };
}
