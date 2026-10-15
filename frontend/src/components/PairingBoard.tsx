import type { TryOnImage } from "../api";
import type { Asset } from "../assets";
import { downloadLogoZip } from "../download";
import type { ProductGroup } from "../pairing";
import { pairModels } from "../pairing";

type Assignments = Record<string, Record<string, string>>;

type Props = {
  groups: ProductGroup[];
  logos: Asset[];
  models: Asset[];
  products: Asset[];
  assignments: Assignments;
  onAssign: (logoStem: string, modelName: string, groupId: string) => void;
  resultCounts: Record<string, number>;
  results: TryOnImage[];
  busy: boolean;
};

function previewByLogicalName(assets: Asset[], name: string): string | undefined {
  return assets.find((asset) => asset.logicalName === name)?.url;
}

function previewByStem(assets: Asset[], name: string): string | undefined {
  return assets.find((asset) => asset.stem === name)?.url;
}

export default function PairingBoard({
  groups,
  logos,
  models,
  products,
  assignments,
  onAssign,
  resultCounts,
  results,
  busy,
}: Props) {
  const modelPhotos = models.map((asset) => ({ name: asset.stem }));
  if (logos.length === 0 || models.length === 0 || groups.length === 0) {
    return (
      <p className="pairing-empty">
        请上传印花、实拍和参考模特后，按印花 × 参考图配置组合。
      </p>
    );
  }

  const total = models.length;

  return (
    <div className="pairing-list">
      {logos.map((logo) => {
        const done = resultCounts[logo.stem] ?? 0;
        const pairs = pairModels(
          modelPhotos,
          groups,
          assignments[logo.stem] ?? null,
        );
        return (
          <section className="logo-group" key={logo.id}>
            <header className="logo-group-head">
              <img src={logo.url} alt={logo.stem} />
              <div>
                <strong>{logo.stem}</strong>
                <p className="logo-progress-line">
                  总张数 {total} · 当前进度 {Math.min(done, total)} / {total}
                  {busy ? "（生成中）" : ""}
                </p>
              </div>
              {!busy && done >= total && total > 0 ? (
                <button
                  type="button"
                  className="logo-download"
                  onClick={() => {
                    void downloadLogoZip(results, logo.stem).catch(() => {
                      window.alert("下载失败");
                    });
                  }}
                >
                  下载
                </button>
              ) : null}
            </header>
            {pairs.map((pair, index) => {
              const selectedId = pair.group.id;
              const group =
                groups.find((item) => item.id === selectedId) ?? pair.group;
              const modelUrl = previewByStem(models, pair.model.name);
              return (
                <article
                  className="pair-row"
                  key={`${logo.id}-${pair.model.name}-${index}`}
                >
                  <div className="pair-who">
                    {modelUrl ? (
                      <img src={modelUrl} alt={pair.model.name} />
                    ) : null}
                    <div>
                      <strong>{pair.model.name}</strong>
                      <small>参考图</small>
                    </div>
                  </div>
                  <span className="pair-arrow" aria-hidden>
                    →
                  </span>
                  <div className="pair-garment">
                    <div className="pair-thumbs">
                      {group.photos.map((photo) => {
                        const url = previewByLogicalName(products, photo.name);
                        return url ? (
                          <img key={photo.name} src={url} alt={photo.name} />
                        ) : null;
                      })}
                    </div>
                    <label>
                      商品
                      <select
                        value={selectedId}
                        onChange={(event) =>
                          onAssign(logo.stem, pair.model.name, event.target.value)
                        }
                      >
                        {groups.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.id}
                            {item.photos.length > 1
                              ? ` · ${item.photos.length} 张角度`
                              : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                </article>
              );
            })}
          </section>
        );
      })}
    </div>
  );
}
