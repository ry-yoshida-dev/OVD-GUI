export interface DisplayOptions {
  isLabelShown: boolean;
  isConfidenceShown: boolean;
  isRejectedShown: boolean;
  isComparedShown: boolean;
  lineWidth: number;
  isFilled: boolean;
}

export const DEFAULT_DISPLAY_OPTIONS: DisplayOptions = {
  isLabelShown: true,
  isConfidenceShown: true,
  isRejectedShown: true,
  isComparedShown: true,
  lineWidth: 2,
  isFilled: false,
};

export function colorOf(palette: string[], classId: number): string {
  return palette.length === 0 ? "#e6194b" : (palette[classId % palette.length] ?? "#e6194b");
}

export function textColorOn(background: string): string {
  const value = Number.parseInt(background.slice(1), 16);
  const red = (value >> 16) & 255;
  const green = (value >> 8) & 255;
  const blue = value & 255;
  return (0.299 * red + 0.587 * green + 0.114 * blue) / 255 > 0.6 ? "#000000" : "#ffffff";
}
