const IMAGE_PATTERN = /\.(jpe?g|png|bmp|webp|tiff?)$/i;

export interface DroppedFile {
  file: File;
  name: string;
}

function readEntries(reader: FileSystemDirectoryReader): Promise<FileSystemEntry[]> {
  return new Promise((resolve, reject) => reader.readEntries(resolve, reject));
}

function fileOf(entry: FileSystemFileEntry): Promise<File> {
  return new Promise((resolve, reject) => entry.file(resolve, reject));
}

async function collect(entry: FileSystemEntry, prefix: string, files: DroppedFile[]): Promise<void> {
  if (entry.isFile) {
    if (IMAGE_PATTERN.test(entry.name) && !entry.name.startsWith(".")) {
      files.push({ file: await fileOf(entry as FileSystemFileEntry), name: `${prefix}${entry.name}` });
    }
    return;
  }
  if (!entry.isDirectory || entry.name.startsWith(".")) return;
  const reader = (entry as FileSystemDirectoryEntry).createReader();
  for (;;) {
    const entries = await readEntries(reader);
    if (entries.length === 0) break;
    for (const child of entries) {
      await collect(child, `${prefix}${entry.name}/`, files);
    }
  }
}

export async function imageFilesOf(transfer: DataTransfer): Promise<DroppedFile[]> {
  const entries = [...transfer.items]
    .filter((item) => item.kind === "file")
    .map((item) => item.webkitGetAsEntry())
    .filter((entry): entry is FileSystemEntry => entry !== null);
  if (entries.length === 0) {
    return [...transfer.files]
      .filter((file) => IMAGE_PATTERN.test(file.name))
      .map((file) => ({ file, name: file.name }));
  }
  const files: DroppedFile[] = [];
  for (const entry of entries) {
    await collect(entry, "", files);
  }
  return files;
}

export function imageFilesOfList(list: FileList | null): DroppedFile[] {
  return [...(list ?? [])]
    .filter((file) => IMAGE_PATTERN.test(file.name))
    .map((file) => ({ file, name: file.webkitRelativePath || file.name }));
}

export function hasFiles(transfer: DataTransfer | null): boolean {
  return transfer !== null && [...transfer.types].includes("Files");
}
