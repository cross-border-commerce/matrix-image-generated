import { fileStem } from "./pairing";

export type Asset = {
  id: string;
  file: File;
  url: string;
  logicalName: string;
  stem: string;
};

export function logicalNameOf(file: File): string {
  const relative = file.webkitRelativePath;
  return relative && relative.length > 0 ? relative : file.name;
}

export function toAsset(file: File): Asset {
  const logicalName = logicalNameOf(file);
  return {
    id: crypto.randomUUID(),
    file,
    url: URL.createObjectURL(file),
    logicalName,
    stem: fileStem(file.name),
  };
}

export function namedFile(file: File, name: string): File {
  if (file.name === name) {
    return file;
  }
  return new File([file], name, {
    type: file.type,
    lastModified: file.lastModified,
  });
}

export function revokeAll(assets: Asset[]): void {
  for (const asset of assets) {
    URL.revokeObjectURL(asset.url);
  }
}
