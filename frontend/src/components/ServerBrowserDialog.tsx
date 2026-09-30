import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { DirectoryListing } from "../api/types";
import { Dialog } from "./Dialog";

export type BrowseMode = "images" | "directory" | "image";

interface ServerBrowserDialogProps {
  mode: BrowseMode;
  title: string;
  initialPath?: string;
  isFolderChoosable?: boolean;
  onChoose: (paths: string[]) => void;
  onClose: () => void;
}

const LAST_DIRECTORY_KEY = "ovd-gui.last-directory";

function joinPath(directory: string, name: string): string {
  const separator = directory.includes("\\") && !directory.includes("/") ? "\\" : "/";
  return directory.endsWith(separator) ? `${directory}${name}` : `${directory}${separator}${name}`;
}

export function ServerBrowserDialog({
  mode,
  title,
  initialPath,
  isFolderChoosable = true,
  onChoose,
  onClose,
}: ServerBrowserDialogProps) {
  const [listing, setListing] = useState<DirectoryListing | null>(null);
  const [pathText, setPathText] = useState("");
  const [error, setError] = useState("");
  const [selectedImages, setSelectedImages] = useState<Set<string>>(new Set());

  const load = useCallback(async (path?: string) => {
    try {
      const next = await api.files(path);
      setListing(next);
      setPathText(next.path);
      setSelectedImages(new Set());
      setError("");
      try {
        window.localStorage.setItem(LAST_DIRECTORY_KEY, next.path);
      } catch {
        /* storage may be unavailable */
      }
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }, []);

  useEffect(() => {
    let remembered: string | undefined;
    try {
      remembered = window.localStorage.getItem(LAST_DIRECTORY_KEY) ?? undefined;
    } catch {
      remembered = undefined;
    }
    void load(initialPath ?? remembered);
  }, [load, initialPath]);

  const chooseTypedPath = () => {
    const typed = pathText.trim();
    if (typed === "") return;
    if (mode === "images" && /\.(jpe?g|png|bmp|webp|tiff?)$/i.test(typed)) {
      onChoose([typed]);
      return;
    }
    void load(typed);
  };

  const selectedPaths = listing === null ? [] : [...selectedImages].map((name) => joinPath(listing.path, name));

  return (
    <Dialog
      title={title}
      onClose={onClose}
      width={640}
      footer={
        <>
          <span className="left hint">
            {mode === "images" && listing !== null && `${listing.images.length} images in this folder`}
          </span>
          <button onClick={onClose}>Cancel</button>
          {mode === "images" && (
            <button disabled={selectedPaths.length === 0} onClick={() => onChoose(selectedPaths)}>
              Open {selectedPaths.length || ""} Selected
            </button>
          )}
          {(mode === "directory" || (mode === "images" && isFolderChoosable)) && (
            <button className="primary" disabled={listing === null} onClick={() => listing && onChoose([listing.path])}>
              {mode === "images" ? "Open This Folder" : "Choose This Folder"}
            </button>
          )}
          {mode === "image" && (
            <button className="primary" disabled={selectedPaths.length !== 1} onClick={() => onChoose(selectedPaths)}>
              Open
            </button>
          )}
        </>
      }
    >
      <div className="file-browser">
        <div className="row">
          <button className="icon" disabled={listing?.parent == null} onClick={() => void load(listing?.parent ?? undefined)} title="Parent folder">
            ↑
          </button>
          <input
            type="text"
            className="grow mono"
            value={pathText}
            onChange={(event) => setPathText(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && chooseTypedPath()}
            placeholder="Path on the server"
          />
          <button onClick={chooseTypedPath}>Go</button>
        </div>
        {listing !== null && listing.shortcuts.length > 0 && (
          <div className="row wrap small">
            {listing.shortcuts.map((shortcut) => (
              <button key={shortcut.name} className="ghost" onClick={() => void load(shortcut.path)} title={shortcut.path}>
                {shortcut.name}
              </button>
            ))}
          </div>
        )}
        {error !== "" && <div className="error-text">{error}</div>}
        <div className="list">
          {listing?.directories.map((name) => (
            <div key={`d-${name}`} className="list-item" onDoubleClick={() => void load(joinPath(listing.path, name))} onClick={() => void load(joinPath(listing.path, name))}>
              <span>📁</span>
              <span className="name">{name}</span>
            </div>
          ))}
          {mode !== "directory" &&
            listing?.images.map((name) => (
              <div
                key={`i-${name}`}
                className={`list-item${selectedImages.has(name) ? " selected" : ""}`}
                onClick={(event) => {
                  setSelectedImages((current) => {
                    if (mode === "image") return new Set([name]);
                    const next = new Set(event.metaKey || event.ctrlKey || event.shiftKey ? current : []);
                    if (next.has(name)) next.delete(name);
                    else next.add(name);
                    return next;
                  });
                }}
                onDoubleClick={() => onChoose([joinPath(listing.path, name)])}
              >
                <span>🖼</span>
                <span className="name">{name}</span>
              </div>
            ))}
          {listing !== null && listing.directories.length === 0 && (mode === "directory" || listing.images.length === 0) && (
            <div className="list-item faint">Empty folder</div>
          )}
        </div>
        <div className="hint">
          {mode === "images"
            ? "Browse the server's file system. Open a whole folder, or select images (Ctrl/⌘-click for several)."
            : mode === "directory"
              ? "Choose the folder on the server that receives the files."
              : "Choose an image on the server."}
        </div>
      </div>
    </Dialog>
  );
}
