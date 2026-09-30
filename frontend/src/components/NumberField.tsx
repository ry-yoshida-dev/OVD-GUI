import { useEffect, useState } from "react";

interface NumberFieldProps {
  value: number;
  onCommit: (value: number) => void;
  minimum?: number;
  maximum?: number;
  step?: number;
  isDisabled?: boolean;
  width?: number;
  title?: string;
}

export function NumberField({
  value,
  onCommit,
  minimum = 0,
  maximum = 1,
  step = 0.05,
  isDisabled = false,
  width,
  title,
}: NumberFieldProps) {
  const [text, setText] = useState(String(value));
  useEffect(() => setText(String(value)), [value]);
  const commit = () => {
    const parsed = Number.parseFloat(text);
    if (Number.isNaN(parsed)) {
      setText(String(value));
      return;
    }
    const clamped = Math.min(maximum, Math.max(minimum, parsed));
    setText(String(clamped));
    if (clamped !== value) onCommit(clamped);
  };
  return (
    <input
      type="number"
      value={text}
      min={minimum}
      max={maximum}
      step={step}
      disabled={isDisabled}
      title={title}
      style={{ width }}
      onChange={(event) => setText(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") commit();
      }}
    />
  );
}
