import { useRef, useState } from "react";

interface SplitterProps {
  onResize: (delta: number) => void;
  isHorizontal?: boolean;
}

export function Splitter({ onResize, isHorizontal = false }: SplitterProps) {
  const last = useRef(0);
  const [isActive, setIsActive] = useState(false);
  return (
    <div
      className={`splitter${isHorizontal ? " horizontal" : ""}${isActive ? " active" : ""}`}
      onPointerDown={(event) => {
        last.current = isHorizontal ? event.clientY : event.clientX;
        setIsActive(true);
        event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={(event) => {
        if (!isActive) return;
        const position = isHorizontal ? event.clientY : event.clientX;
        onResize(position - last.current);
        last.current = position;
      }}
      onPointerUp={() => setIsActive(false)}
      onPointerCancel={() => setIsActive(false)}
    />
  );
}
