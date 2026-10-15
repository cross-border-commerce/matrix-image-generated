import JSZip from "jszip";
import type { TryOnImage } from "./api";

export function filenameFromUrl(url: string): string {
  const path = url.split("?")[0];
  return decodeURIComponent(path.split("/").pop() || "image.png");
}

function triggerDownload(blob: Blob, name: string): void {
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  link.click();
  URL.revokeObjectURL(href);
}

export function imagesForLogo(images: TryOnImage[], logoStem: string): TryOnImage[] {
  return images.filter((image) => image.logo === logoStem);
}

export async function downloadImagesZip(
  files: { path: string; url: string }[],
  zipName: string,
): Promise<void> {
  const zip = new JSZip();
  for (const file of files) {
    const response = await fetch(file.url);
    if (!response.ok) {
      throw new Error(`下载失败 ${file.path}`);
    }
    zip.file(file.path, await response.blob());
  }
  triggerDownload(await zip.generateAsync({ type: "blob" }), zipName);
}

export async function downloadLogoZip(
  images: TryOnImage[],
  logoStem: string,
): Promise<void> {
  const files = imagesForLogo(images, logoStem).map((image) => ({
    path: filenameFromUrl(image.url),
    url: image.url,
  }));
  if (files.length === 0) {
    throw new Error("这个印花还没有生成图");
  }
  await downloadImagesZip(files, `${logoStem}.zip`);
}

export async function downloadAllByLogo(images: TryOnImage[]): Promise<void> {
  const files = images.map((image) => {
    const folder = image.logo || "未分组";
    return {
      path: `${folder}/${filenameFromUrl(image.url)}`,
      url: image.url,
    };
  });
  if (files.length === 0) {
    throw new Error("还没有可下载的结果");
  }
  await downloadImagesZip(files, "电商图.zip");
}
