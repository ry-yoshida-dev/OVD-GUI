import { useEffect, useRef, useState } from "react";
import type { ImageEntry } from "../api/types";
import { useMenu } from "./Menu";

interface ImageListProps {
  images: ImageEntry[];
  currentPath: string | null;
  backgroundPath: string | null;
  onSelect: (path: string) => void;
  onClose: (paths: string[]) => void;
}

export function ImageList({ images, currentPath, backgroundPath, onSelect, onClose }: ImageListProps) {
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const anchor = useRef<string | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const menu = useMenu();

  useEffect(() => {
    const open = new Set(images.map((image) => image.path));
    setSelectedPaths((current) => new Set([...current].filter((path) => open.has(path))));
  }, [images]);

  useEffect(() => {
    if (currentPath === null) return;
    const element = container.current?.querySelector<HTMLElement>(`[data-path="${CSS.escape(currentPath)}"]`);
    element?.scrollIntoView({ block: "nearest" });
  }, [currentPath]);

  const effectiveSelection = (): string[] => {
    if (selectedPaths.size > 0) return images.map((image) => image.path).filter((path) => selectedPaths.has(path));
    return currentPath === null ? [] : [currentPath];
  };

  const step = (delta: number) => {
    const index = images.findIndex((image) => image.path === currentPath);
    const next = images[Math.min(images.length - 1, Math.max(0, index + delta))];
    if (next !== undefined && next.path !== currentPath) {
      setSelectedPaths(new Set());
      onSelect(next.path);
    }
  };

  const onRowClick = (event: React.MouseEvent, path: string) => {
    if (event.metaKey || event.ctrlKey) {
      setSelectedPaths((current) => {
        const next = new Set(current.size === 0 && currentPath !== null ? [currentPath] : current);
        if (next.has(path)) next.delete(path);
        else next.add(path);
        return next;
      });
      anchor.current = path;
      return;
    }
    if (event.shiftKey && anchor.current !== null) {
      const from = images.findIndex((image) => image.path === anchor.current);
      const to = images.findIndex((image) => image.path === path);
      const [start, end] = from < to ? [from, to] : [to, from];
      setSelectedPaths(new Set(images.slice(start, end + 1).map((image) => image.path)));
      return;
    }
    anchor.current = path;
    setSelectedPaths(new Set());
    onSelect(path);
  };

  return (
    <>
      <div
        ref={container}
        className="list"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "ArrowUp" || event.key === "ArrowLeft" || event.key === "PageUp") {
            event.preventDefault();
            step(-1);
          } else if (event.key === "ArrowDown" || event.key === "ArrowRight" || event.key === "PageDown") {
            event.preventDefault();
            step(1);
          } else if (event.key === "Delete" || event.key === "Backspace") {
            event.preventDefault();
            const paths = effectiveSelection();
            if (paths.length > 0) onClose(paths);
          }
        }}
      >
        {images.length === 0 && <div className="list-item faint">No images open.</div>}
        {images.map((image) => {
          const isCurrent = image.path === currentPath;
          const isSelected = selectedPaths.has(image.path);
          return (
            <div
              key={image.path}
              data-path={image.path}
              className={`list-item${isCurrent ? " current" : ""}${isSelected && !isCurrent ? " selected" : ""}`}
              title={`${image.path}\n${image.description}`}
              onClick={(event) => onRowClick(event, image.path)}
              onContextMenu={(event) => {
                event.preventDefault();
                if (!selectedPaths.has(image.path) && image.path !== currentPath) {
                  setSelectedPaths(new Set([image.path]));
                }
                const paths = selectedPaths.has(image.path) ? effectiveSelection() : [image.path];
                menu.open(event.clientX, event.clientY, [
                  {
                    label: paths.length === 1 ? "Close Image" : `Close ${paths.length} Images`,
                    shortcut: "Del",
                    onSelect: () => onClose(paths),
                  },
                  { label: "Close All Images", onSelect: () => onClose(images.map((entry) => entry.path)) },
                ]);
              }}
            >
              <span
                className="dot"
                style={{
                  borderColor: image.color,
                  background: image.is_marked_filled ? image.color : "transparent",
                }}
              />
              <span className="name">{image.name}</span>
              {image.path === backgroundPath && <span className="faint small">detecting…</span>}
              <span className="muted small">{image.count_text}</span>
            </div>
          );
        })}
      </div>
      {menu.element}
    </>
  );
}
