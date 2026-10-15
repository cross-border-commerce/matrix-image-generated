import type { ChangeEvent } from "react";
import type { Asset } from "../assets";

type Props = {
  title: string;
  hint: string;
  assets: Asset[];
  onAdd: (files: FileList) => void;
  onRemove: (id: string) => void;
  allowDirectory?: boolean;
};

export default function UploadZone({
  title,
  hint,
  assets,
  onAdd,
  onRemove,
  allowDirectory = false,
}: Props) {
  const onFiles = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      onAdd(event.target.files);
    }
    event.target.value = "";
  };

  return (
    <section className="upload-card">
      <header>
        <h2>{title}</h2>
        <p>{hint}</p>
      </header>
      <div className="upload-actions">
        <label className="file-btn">
          选择图片
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple
            onChange={onFiles}
          />
        </label>
        {allowDirectory ? (
          <label className="file-btn ghost">
            选择文件夹
            <input
              type="file"
              multiple
              // @ts-expect-error webkitdirectory is a non-standard attribute
              webkitdirectory=""
              onChange={onFiles}
            />
          </label>
        ) : null}
      </div>
      {assets.length > 0 ? (
        <ul className="thumb-list">
          {assets.map((asset) => (
            <li key={asset.id}>
              <img src={asset.url} alt={asset.logicalName} />
              <span title={asset.logicalName}>{asset.logicalName}</span>
              <button type="button" onClick={() => onRemove(asset.id)}>
                移除
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="empty-slot">png / jpg / webp</div>
      )}
    </section>
  );
}
