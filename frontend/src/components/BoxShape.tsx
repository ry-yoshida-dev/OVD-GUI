import type { Box } from "../api/types";
import { textColorOn } from "../lib/displayOptions";

export type BoxRole = "kept" | "rejected" | "compared" | "reference";

interface BoxShapeProps {
  box: Box;
  color: string;
  role: BoxRole;
  scale: number;
  lineWidth: number;
  isFilled: boolean;
  isHighlighted?: boolean;
  label?: string;
  onClick?: () => void;
}

const LABEL_FONT_SIZE = 12;
const LABEL_PADDING = 3;

export function BoxShape({
  box,
  color,
  role,
  scale,
  lineWidth,
  isFilled,
  isHighlighted = false,
  label,
  onClick,
}: BoxShapeProps) {
  const [left, top, right, bottom] = box;
  const width = Math.max(0, right - left);
  const height = Math.max(0, bottom - top);
  const dash = role === "rejected" ? "7 4" : role === "compared" ? "2 3" : role === "reference" ? "8 4" : undefined;
  const opacity = role === "rejected" ? 0.55 : 1;
  const strokeWidth = isHighlighted ? lineWidth + 2 : lineWidth;
  const fontSize = LABEL_FONT_SIZE / scale;
  const padding = LABEL_PADDING / scale;
  const labelHeight = fontSize + padding * 2;
  const labelWidth = label === undefined ? 0 : label.length * fontSize * 0.6 + padding * 2;
  const labelTop = top - labelHeight >= 0 ? top - labelHeight : top;
  return (
    <g
      opacity={opacity}
      onPointerDown={(event) => {
        if (onClick !== undefined && event.button === 0 && !event.shiftKey) {
          event.stopPropagation();
          onClick();
        }
      }}
      style={{ cursor: onClick === undefined ? undefined : "pointer" }}
    >
      {isHighlighted && (
        <rect
          x={left}
          y={top}
          width={width}
          height={height}
          fill="none"
          stroke="#ffffff"
          strokeWidth={strokeWidth + 3}
          vectorEffect="non-scaling-stroke"
        />
      )}
      <rect
        x={left}
        y={top}
        width={width}
        height={height}
        fill={isFilled || isHighlighted ? color : "transparent"}
        fillOpacity={isHighlighted ? 0.22 : isFilled ? 0.18 : 0}
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={dash}
        vectorEffect="non-scaling-stroke"
        pointerEvents={onClick === undefined ? "none" : "all"}
      />
      {label !== undefined && label !== "" && (
        <g pointerEvents="none">
          <rect x={left} y={labelTop} width={labelWidth} height={labelHeight} fill={color} />
          <text
            x={left + padding}
            y={labelTop + padding + fontSize * 0.85}
            fontSize={fontSize}
            fill={textColorOn(color)}
            fontFamily="ui-monospace, Menlo, Consolas, monospace"
          >
            {label}
          </text>
        </g>
      )}
    </g>
  );
}
