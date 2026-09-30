import { useRef, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { Box, ClassEntry, ReferenceDraft } from "../api/types";
import { hasFiles, imageFilesOf, imageFilesOfList } from "../lib/droppedFiles";
import { BoxShape } from "./BoxShape";
import { Dialog } from "./Dialog";
import { ServerBrowserDialog } from "./ServerBrowserDialog";
import { ZoomableImage } from "./ZoomableImage";

interface ReferenceDialogProps {
  classIndex: number;
  classEntry: ClassEntry;
  onAdded: (count: number) => void;
  onClose: () => void;
}

export function ReferenceDialog({ classIndex, classEntry, onAdded, onClose }: ReferenceDialogProps) {
  const [queue, setQueue] = useState<ReferenceDraft[]>([]);
  const [boxes, setBoxes] = useState<Box[]>([]);
  const [selectedBox, setSelectedBox] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isBrowsing, setIsBrowsing] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [addedCount, setAddedCount] = useState(0);
  const [error, setError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const current = queue[0] ?? null;

  const enqueue = async (loaders: (() => Promise<ReferenceDraft>)[]) => {
    setIsLoading(true);
    setError("");
    for (const load of loaders) {
      try {
        const draft = await load();
        setQueue((existing) => [...existing, draft]);
      } catch (caught) {
        setError(errorMessage(caught));
      }
    }
    setIsLoading(false);
  };

  const advance = () => {
    setQueue((existing) => existing.slice(1));
    setBoxes([]);
    setSelectedBox(null);
  };

  const submit = async (submitted: Box[]) => {
    if (current === null) return;
    try {
      await api.addReference(current.draft_id, classIndex, submitted);
      setAddedCount((count) => count + 1);
      onAdded(1);
      advance();
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  return (
    <>
      <Dialog
        title={
          <span>
            Image Prompts of <span className="swatch" style={{ background: classEntry.color, display: "inline-block", verticalAlign: -1 }} />{" "}
            {classEntry.name}
          </span>
        }
        onClose={onClose}
        width={current === null ? 560 : "min(1100px, 94vw)"}
        height={current === null ? undefined : "min(820px, 92vh)"}
        footer={
          current === null ? (
            <>
              <span className="left hint">{addedCount > 0 ? `${addedCount} images added.` : ""}</span>
              <button onClick={onClose}>{addedCount > 0 ? "Done" : "Cancel"}</button>
            </>
          ) : (
            <>
              <span className="left hint">
                {queue.length > 1 ? `${queue.length - 1} more images waiting · ` : ""}Drag to draw boxes around the
                examples; Shift-drag or wheel to move and zoom.
              </span>
              <button onClick={advance}>Skip</button>
              <button onClick={() => void submit([])}>Use Whole Image</button>
              <button className="primary" disabled={boxes.length === 0} onClick={() => void submit(boxes)}>
                Add {boxes.length} Box{boxes.length === 1 ? "" : "es"}
              </button>
            </>
          )
        }
      >
        {error !== "" && <div className="error-text">{error}</div>}
        {current === null ? (
          <div
            className="drop-zone"
            style={{
              borderColor: isDragOver ? "var(--accent)" : "var(--border-strong)",
              maxWidth: "none",
              background: isDragOver ? "var(--accent-soft)" : undefined,
            }}
            onDragEnter={(event) => {
              if (!hasFiles(event.dataTransfer)) return;
              event.preventDefault();
              event.stopPropagation();
              setIsDragOver(true);
            }}
            onDragOver={(event) => {
              if (!hasFiles(event.dataTransfer)) return;
              event.preventDefault();
              event.stopPropagation();
              event.dataTransfer.dropEffect = "copy";
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(event) => {
              event.preventDefault();
              event.stopPropagation();
              setIsDragOver(false);
              void imageFilesOf(event.dataTransfer).then((files) =>
                enqueue(files.map((entry) => () => api.uploadReference(entry.file))),
              );
            }}
          >
            <div style={{ fontWeight: 600 }}>{isLoading ? "Opening images…" : "Drop example images of this class here"}</div>
            <div className="hint">
              Each image becomes one image prompt of the class. Box the examples on it, or use the whole image.
            </div>
            <div className="row">
              <button onClick={() => fileInput.current?.click()}>Choose Files…</button>
              <button onClick={() => setIsBrowsing(true)}>From Server…</button>
            </div>
          </div>
        ) : (
          <div style={{ position: "relative", flex: 1, minHeight: 360, borderRadius: 8, overflow: "hidden", background: "var(--canvas)" }}>
            <ZoomableImage
              src={api.draftImageUrl(current.draft_id)}
              width={current.width}
              height={current.height}
              isDrawing
              drawColor={classEntry.color}
              onDrawn={(box) => {
                setBoxes((existing) => [...existing, box]);
                setSelectedBox(null);
              }}
              onBackgroundClick={() => setSelectedBox(null)}
              onKeyDown={(event) => {
                if ((event.key === "Delete" || event.key === "Backspace") && selectedBox !== null) {
                  setBoxes((existing) => existing.filter((_, index) => index !== selectedBox));
                  setSelectedBox(null);
                }
                if (event.key === "z" && (event.metaKey || event.ctrlKey)) setBoxes((existing) => existing.slice(0, -1));
              }}
              hud={<span> · {current.name} · click a box and press Delete to remove it</span>}
            >
              {(scale) =>
                boxes.map((box, index) => (
                  <BoxShape
                    key={index}
                    box={box}
                    color={classEntry.color}
                    role="reference"
                    scale={scale}
                    lineWidth={2}
                    isFilled
                    isHighlighted={index === selectedBox}
                    label={`${classEntry.name} ${index + 1}`}
                    onClick={() => setSelectedBox(index)}
                  />
                ))
              }
            </ZoomableImage>
          </div>
        )}
        <input
          ref={fileInput}
          type="file"
          accept="image/*,.tif,.tiff"
          multiple
          hidden
          onChange={(event) => {
            const files = imageFilesOfList(event.target.files);
            event.target.value = "";
            void enqueue(files.map((entry) => () => api.uploadReference(entry.file)));
          }}
        />
      </Dialog>
      {isBrowsing && (
        <ServerBrowserDialog
          mode="images"
          title="Open Example Images"
          isFolderChoosable={false}
          onChoose={(paths) => {
            setIsBrowsing(false);
            void enqueue(paths.map((path) => () => api.openReference(path)));
          }}
          onClose={() => setIsBrowsing(false)}
        />
      )}
    </>
  );
}
