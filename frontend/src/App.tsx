import { useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { createTryOnJob, waitForJob, type TryOnImage } from "./api";
import { downloadAllByLogo } from "./download";
import {
  namedFile,
  revokeAll,
  toAsset,
  type Asset,
} from "./assets";
import PairingBoard from "./components/PairingBoard";
import ResultGrid from "./components/ResultGrid";
import UploadZone from "./components/UploadZone";
import { groupModels, groupProducts, outputCount } from "./pairing";
import "./App.css";

export default function App() {
  const [logos, setLogos] = useState<Asset[]>([]);
  const [products, setProducts] = useState<Asset[]>([]);
  const [models, setModels] = useState<Asset[]>([]);
  const [assignments, setAssignments] = useState<
    Record<string, Record<string, string>>
  >({});
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [results, setResults] = useState<TryOnImage[]>([]);
  const [zipping, setZipping] = useState(false);

  const groups = useMemo(
    () => groupProducts(products.map((asset) => ({ name: asset.logicalName }))),
    [products],
  );
  const modelGroups = useMemo(
    () => groupModels(models.map((asset) => ({ name: asset.logicalName }))),
    [models],
  );
  const expected = outputCount(modelGroups, logos.length);
  const canGenerate =
    logos.length > 0 && products.length > 0 && models.length > 0;
  const resultCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const image of results) {
      if (!image.logo) {
        continue;
      }
      counts[image.logo] = (counts[image.logo] ?? 0) + 1;
    }
    return counts;
  }, [results]);

  const addAssets = (
    setter: Dispatch<SetStateAction<Asset[]>>,
    files: FileList,
  ) => {
    const incoming = Array.from(files)
      .filter(
        (file) =>
          file.type.startsWith("image/") ||
          /\.(png|jpe?g|webp)$/i.test(file.name),
      )
      .map(toAsset);
    setter((current) => [...current, ...incoming]);
  };

  const removeAsset = (
    setter: Dispatch<SetStateAction<Asset[]>>,
    id: string,
  ) => {
    setter((current) => {
      const target = current.find((asset) => asset.id === id);
      if (target) {
        URL.revokeObjectURL(target.url);
      }
      return current.filter((asset) => asset.id !== id);
    });
  };

  const generate = async () => {
    setError("");
    setResults([]);
    if (logos.length === 0 || products.length === 0 || models.length === 0) {
      setError("请上传印花、实拍和参考模特，三类图都需要。");
      return;
    }
    setBusy(true);
    setStatus("正在提交任务…");
    try {
      const payloadAssignments =
        Object.keys(assignments).length > 0 ? assignments : undefined;
      const job = await createTryOnJob({
        products: products.map((asset) =>
          namedFile(asset.file, asset.logicalName),
        ),
        models: models.map((asset) =>
          namedFile(asset.file, asset.logicalName),
        ),
        logos: logos.map((asset) => asset.file),
        assignments: payloadAssignments,
      });
      const finished = await waitForJob(job.id, (current) => {
        setResults(current.try_on_images);
        const done = current.try_on_images.length;
        const label =
          current.status === "pending"
            ? "排队中"
            : current.status === "running"
              ? "生成中"
              : current.status;
        setStatus(`${label} · ${done} / ${expected}`);
      });
      if (finished.status === "failed") {
        setError(finished.error || "生成失败");
        setStatus("");
        return;
      }
      setResults(finished.try_on_images);
      setStatus(`完成 ${finished.try_on_images.length} 张`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
      setStatus("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <p className="eyebrow">Matrix Image Studio</p>
        <h1>把印花、成衣实拍和模特参考合成电商图</h1>
        <p className="lede">
          一个印花配一组参考图。子目录各算一组，没有子目录则全部算一组。组内每张参考图配一件实拍，不够就循环。
        </p>
      </header>

      <div className="upload-grid">
        <UploadZone
          title="印花 Logo"
          hint="必填。支持选文件夹。"
          assets={logos}
          allowDirectory
          onAdd={(files) => addAssets(setLogos, files)}
          onRemove={(id) => removeAsset(setLogos, id)}
        />
        <UploadZone
          title="工厂实拍"
          hint="同目录或去掉正面/背面后词干相同的，算同一件。"
          assets={products}
          allowDirectory
          onAdd={(files) => addAssets(setProducts, files)}
          onRemove={(id) => removeAsset(setProducts, id)}
        />
        <UploadZone
          title="参考模特"
          hint="选一个目录。子目录各算一组；没有子目录则全部算一组。"
          assets={models}
          allowDirectory
          onAdd={(files) => addAssets(setModels, files)}
          onRemove={(id) => removeAsset(setModels, id)}
        />
      </div>

      <section className="board">
        <div className="board-head">
          <div>
            <h2>配对</h2>
            <p>
              {canGenerate
                ? "每个印花配一组参考图。组内每张可改配哪件商品。"
                : "请先上传印花、实拍和参考图。"}
            </p>
            {status ? <p className="status">{status}</p> : null}
          </div>
          <div className="board-actions">
            <button
              type="button"
              className="clear"
              disabled={busy}
              onClick={() => {
                revokeAll([...logos, ...products, ...models]);
                setLogos([]);
                setProducts([]);
                setModels([]);
                setAssignments({});
                setResults([]);
                setError("");
                setStatus("");
              }}
            >
              清空素材
            </button>
            <button
              type="button"
              className="generate"
              disabled={busy || !canGenerate}
              onClick={generate}
            >
              {busy ? "生成中…" : "生成电商图"}
            </button>
          </div>
        </div>
        <PairingBoard
          groups={groups}
          logos={logos}
          models={models}
          products={products}
          assignments={assignments}
          resultCounts={resultCounts}
          results={results}
          busy={busy}
          modelGroups={modelGroups}
          onAssign={(logoStem, rowKey, groupId) =>
            setAssignments((current) => ({
              ...current,
              [logoStem]: { ...current[logoStem], [rowKey]: groupId },
            }))
          }
        />
      </section>

      {error ? <p className="error">{error}</p> : null}

      <section className="results">
        <div className="board-head">
          <h2>结果</h2>
          {results.length > 0 ? (
            <button
              type="button"
              className="logo-download"
              disabled={zipping}
              onClick={() => {
                setZipping(true);
                void downloadAllByLogo(results)
                  .catch(() => {
                    window.alert("打包失败");
                  })
                  .finally(() => {
                    setZipping(false);
                  });
              }}
            >
              {zipping ? "打包中…" : "下载全部"}
            </button>
          ) : null}
        </div>
        {results.length === 0 ? (
          <p className="pairing-empty">生成完成后会显示在这里，可直接下载。</p>
        ) : (
          <ResultGrid images={results} />
        )}
      </section>
    </div>
  );
}
