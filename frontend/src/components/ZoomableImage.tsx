import { type KeyboardEvent, type ReactNode, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Box } from "../api/types";

interface View {
  scale: number;
  x: number;
  y: number;
}

interface ZoomableImageProps {
  src: string;
  width: number;
  height: number;
  children?: (scale: number) => ReactNode;
  isDrawing?: boolean;
  drawColor?: string;
  onDrawn?: (box: Box) => void;
  onKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
  onBackgroundClick?: () => void;
  hud?: ReactNode;
}

const MIN_DRAWN_SIDE = 3;
const FIT_MARGIN = 0.96;

export function ZoomableImage({
  src,
  width,
  height,
  children,
  isDrawing = false,
  drawColor = "#ffcc00",
  onDrawn,
  onKeyDown,
  onBackgroundClick,
  hud,
}: ZoomableImageProps) {
  const container = useRef<HTMLDivElement>(null);
  const [view, setView] = useState<View>({ scale: 1, x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [draft, setDraft] = useState<Box | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const isUserZoomed = useRef(false);
  const gesture = useRef<
    | { kind: "pan"; startX: number; startY: number; view: View; hasMoved: boolean }
    | { kind: "draw"; start: [number, number] }
    | null
  >(null);

  const fit = useCallback(() => {
    const element = container.current;
    if (element === null || width <= 0 || height <= 0) return;
    const bounds = element.getBoundingClientRect();
    const scale = Math.min(bounds.width / width, bounds.height / height) * FIT_MARGIN;
    setView({ scale, x: (bounds.width - width * scale) / 2, y: (bounds.height - height * scale) / 2 });
    isUserZoomed.current = false;
  }, [width, height]);

  useLayoutEffect(() => {
    fit();
  }, [fit, src]);

  useEffect(() => {
    setIsLoaded(false);
  }, [src]);

  useEffect(() => {
    const element = container.current;
    if (element === null) return;
    const observer = new ResizeObserver(() => {
      if (!isUserZoomed.current) fit();
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [fit]);

  useEffect(() => {
    const element = container.current;
    if (element === null) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const bounds = element.getBoundingClientRect();
      const pointerX = event.clientX - bounds.left;
      const pointerY = event.clientY - bounds.top;
      const factor = Math.exp(-event.deltaY * (event.ctrlKey ? 0.01 : 0.0015));
      setView((current) => {
        const scale = Math.min(64, Math.max(0.02, current.scale * factor));
        const ratio = scale / current.scale;
        return { scale, x: pointerX - (pointerX - current.x) * ratio, y: pointerY - (pointerY - current.y) * ratio };
      });
      isUserZoomed.current = true;
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, []);

  const toImage = (clientX: number, clientY: number): [number, number] => {
    const bounds = container.current?.getBoundingClientRect();
    const left = bounds?.left ?? 0;
    const top = bounds?.top ?? 0;
    const x = (clientX - left - view.x) / view.scale;
    const y = (clientY - top - view.y) / view.scale;
    return [Math.min(width, Math.max(0, x)), Math.min(height, Math.max(0, y))];
  };

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    container.current?.focus();
    if (event.button === 1 || (event.button === 0 && (!isDrawing || event.shiftKey || event.altKey))) {
      gesture.current = { kind: "pan", startX: event.clientX, startY: event.clientY, view, hasMoved: false };
      setIsPanning(true);
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }
    if (event.button === 0 && isDrawing) {
      const start = toImage(event.clientX, event.clientY);
      gesture.current = { kind: "draw", start };
      setDraft([start[0], start[1], start[0], start[1]]);
      event.currentTarget.setPointerCapture(event.pointerId);
    }
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const current = gesture.current;
    if (current === null) return;
    if (current.kind === "pan") {
      const deltaX = event.clientX - current.startX;
      const deltaY = event.clientY - current.startY;
      if (Math.abs(deltaX) + Math.abs(deltaY) > 3) current.hasMoved = true;
      setView({ scale: current.view.scale, x: current.view.x + deltaX, y: current.view.y + deltaY });
      isUserZoomed.current = true;
      return;
    }
    const point = toImage(event.clientX, event.clientY);
    setDraft([current.start[0], current.start[1], point[0], point[1]]);
  };

  const onPointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    const current = gesture.current;
    gesture.current = null;
    setIsPanning(false);
    if (current?.kind === "pan" && !current.hasMoved && event.target === event.currentTarget.querySelector("image")) {
      onBackgroundClick?.();
    }
    if (current?.kind === "draw" && draft !== null) {
      const box: Box = [
        Math.min(draft[0], draft[2]),
        Math.min(draft[1], draft[3]),
        Math.max(draft[0], draft[2]),
        Math.max(draft[1], draft[3]),
      ];
      setDraft(null);
      if (box[2] - box[0] >= MIN_DRAWN_SIDE && box[3] - box[1] >= MIN_DRAWN_SIDE) onDrawn?.(box);
    }
  };

  return (
    <div
      ref={container}
      className={`viewer${isPanning ? " panning" : ""}${isDrawing && !isPanning ? " drawing" : ""}`}
      tabIndex={0}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={() => {
        gesture.current = null;
        setIsPanning(false);
        setDraft(null);
      }}
      onDoubleClick={fit}
      onKeyDown={onKeyDown}
    >
      <svg>
        <g transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
          <image
            href={src}
            width={width}
            height={height}
            preserveAspectRatio="none"
            onLoad={() => setIsLoaded(true)}
            style={{ imageRendering: view.scale > 3 ? "pixelated" : "auto" }}
          />
          {isLoaded && children?.(view.scale)}
          {draft !== null && (
            <rect
              x={Math.min(draft[0], draft[2])}
              y={Math.min(draft[1], draft[3])}
              width={Math.abs(draft[2] - draft[0])}
              height={Math.abs(draft[3] - draft[1])}
              fill="none"
              stroke={drawColor}
              strokeWidth={2}
              strokeDasharray="6 3"
              vectorEffect="non-scaling-stroke"
            />
          )}
        </g>
      </svg>
      <div className="viewer-hud">
        {Math.round(view.scale * 100)}%{hud}
      </div>
    </div>
  );
}
