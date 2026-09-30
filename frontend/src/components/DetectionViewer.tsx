import { api } from "../api/client";
import type { CurrentImage, Detection } from "../api/types";
import { colorOf, type DisplayOptions } from "../lib/displayOptions";
import { BoxShape } from "./BoxShape";
import { ZoomableImage } from "./ZoomableImage";

interface DetectionViewerProps {
  image: CurrentImage | null;
  detections: Detection[];
  listedIndices: Set<number> | null;
  highlightedIndex: number | null;
  options: DisplayOptions;
  palette: string[];
  isImageListEmpty: boolean;
  onSelectDetection: (index: number) => void;
  onClearSelection: () => void;
  onNavigate: (step: number) => void;
  onUploadRequested: () => void;
  onBrowseRequested: () => void;
}

function labelOf(detection: Detection, options: DisplayOptions, prefix = ""): string | undefined {
  if (!options.isLabelShown) return undefined;
  const confidence = options.isConfidenceShown ? ` ${detection.confidence.toFixed(2)}` : "";
  return `${prefix}${detection.class_name}${confidence}`;
}

export function DetectionViewer({
  image,
  detections,
  listedIndices,
  highlightedIndex,
  options,
  palette,
  isImageListEmpty,
  onSelectDetection,
  onClearSelection,
  onNavigate,
  onUploadRequested,
  onBrowseRequested,
}: DetectionViewerProps) {
  if (image === null || image.width === null || image.height === null) {
    return (
      <div className="empty-center">
        {isImageListEmpty ? (
          <div className="drop-zone">
            <div className="headline">Drop images or folders here</div>
            <div className="small" style={{ color: "#aab0b8" }}>
              Dropped files are uploaded to the server. Images already on the server can be opened by path.
            </div>
            <div className="row">
              <button onClick={onUploadRequested}>Upload Images…</button>
              <button onClick={onBrowseRequested}>Open from Server…</button>
            </div>
          </div>
        ) : image === null ? (
          <span>Select an image.</span>
        ) : (
          <span>Cannot read {image.name}.</span>
        )}
      </div>
    );
  }
  const visible = detections.filter(
    (detection) =>
      (listedIndices === null || listedIndices.has(detection.index)) &&
      (detection.is_accepted || options.isRejectedShown),
  );
  const compared = options.isComparedShown ? image.compared_detections : [];
  const comparedPrefix = image.compared_model_name === null ? "" : `${image.compared_model_name}: `;
  return (
    <ZoomableImage
      src={api.imageUrl(image.path, image.version)}
      width={image.width}
      height={image.height}
      onBackgroundClick={onClearSelection}
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft" || event.key === "PageUp") {
          event.preventDefault();
          onNavigate(-1);
        } else if (event.key === "ArrowRight" || event.key === "PageDown") {
          event.preventDefault();
          onNavigate(1);
        }
      }}
      hud={
        <span>
          {" · "}
          {image.name} ({image.width}×{image.height}) · {visible.length} boxes
        </span>
      }
    >
      {(scale) => (
        <>
          {compared.map((detection) => (
            <BoxShape
              key={`compared-${detection.index}`}
              box={detection.box}
              color={colorOf(palette, detection.class_id)}
              role="compared"
              scale={scale}
              lineWidth={options.lineWidth}
              isFilled={false}
              label={labelOf(detection, options, comparedPrefix)}
            />
          ))}
          {visible
            .filter((detection) => detection.index !== highlightedIndex)
            .map((detection) => (
              <BoxShape
                key={detection.index}
                box={detection.box}
                color={colorOf(palette, detection.class_id)}
                role={detection.is_accepted ? "kept" : "rejected"}
                scale={scale}
                lineWidth={options.lineWidth}
                isFilled={options.isFilled}
                label={labelOf(detection, options)}
                onClick={() => onSelectDetection(detection.index)}
              />
            ))}
          {visible
            .filter((detection) => detection.index === highlightedIndex)
            .map((detection) => (
              <BoxShape
                key={detection.index}
                box={detection.box}
                color={colorOf(palette, detection.class_id)}
                role={detection.is_accepted ? "kept" : "rejected"}
                scale={scale}
                lineWidth={options.lineWidth}
                isFilled={options.isFilled}
                isHighlighted
                label={labelOf(detection, options)}
                onClick={() => onSelectDetection(detection.index)}
              />
            ))}
        </>
      )}
    </ZoomableImage>
  );
}
