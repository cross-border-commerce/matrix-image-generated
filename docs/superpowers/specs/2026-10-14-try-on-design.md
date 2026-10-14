# 独立换装接口设计

## 背景

现有链路是 `POST /jobs`：印花 logo + 工厂纯色实拍 → 带印花商品图。编排为 LangGraph `ingest → generate`，生图用 OpenAI `images.edit`。

需要补上独立换装：把商品成衣图穿到模特参考图上。与印花任务解耦，方便后期换模型或改提示词。

## 目标

- 提供独立异步任务 `POST /try-on-jobs`，一次上传多张商品图和多张模特图。
- LangGraph 只 `invoke` 一次；`try_on` 节点内对商品图 × 模特图做全组合。
- 每一次 `images.edit` 仍是 1 张模特图 + 1 张商品图。
- 换装结果尽量保留模特的脸、身材、姿势、背景和光线，只替换服装。
- 印花 `POST /jobs` 行为不变。

## 非目标

- 不把换装接进现有印花任务。
- 不在本阶段接入专用虚拟试衣模型。
- 不支持部分成功：某一对失败则整次任务失败。
- 不做 LangGraph `Send` 并行扇出。

## 架构

```
POST /try-on-jobs  (products[], models[])
  → 落盘 data/try-on-jobs/{id}/
  → 后台 graph.invoke 一次
       ingest（校验全部商品图、模特图）
       → try_on（全组合，每对 edit 一次）
  → GET /try-on-jobs/{id} 查状态与 URL
  → GET /try-on-jobs/{id}/files/{filename} 下载
```

复用现有 `ImageEditor` / `OpenAIImageEditor`。换装提示词独立，印花提示词不动。

任务存储与印花任务使用同一套 `JobStore` 类，但在 `create_app` 里用两个实例，避免两类任务 ID 互相查询。

## 状态与节点

```python
# 商品图、模特图都复用 ProductPhoto：{name, photo_path}

class TryOnImage(TypedDict):
    product_name: str
    model_name: str
    path: Path

class TryOnState(TypedDict, total=False):
    products: list[Path] | list[ProductPhoto]
    models: list[Path] | list[ProductPhoto]
    try_on_images: list[TryOnImage]
```

`ingest_try_on(products, models)`：

- 商品图、模特图都至少 1 张，否则 `IngestError`
- 后缀必须在 `ALLOWED_IMAGE_SUFFIXES`（`.png` / `.jpg` / `.jpeg` / `.webp`）
- 返回 `products`、`models` 列表，`name` 取文件 stem

`build_try_on_graph(editor, output_dir)`：

- `ingest` → `try_on` → END
- `try_on` 外层按商品图顺序、内层按模特图顺序
- 每次 `editor.edit([model_path, product_path], TRY_ON_PROMPT)`
- 写出 `out/{product_name}__{model_name}.png`

## 提示词

第一张参考图是模特图，第二张是商品成衣图。把商品图上的衣服穿到模特身上。脸、身材、姿势、背景、光线保持原样，只换衣服。保留款式、颜色、面料和印花，贴合身体与褶皱光影。不要文字、水印、额外配饰或品牌标识。

运行时不插变量。

## API

### `POST /try-on-jobs`（multipart，202）

| 字段 | 说明 |
| --- | --- |
| `products` | 1 张或多张商品成衣图 |
| `models` | 1 张或多张模特参考图 |

缺字段或空列表：422。格式不合法：任务 `failed`（ingest 抛 `IngestError`）。

落盘：

```
data/try-on-jobs/{id}/
  products/
  models/
  product_order.txt
  model_order.txt
  out/
```

### `GET /try-on-jobs/{id}`

```json
{
  "id": "...",
  "status": "pending | running | succeeded | failed",
  "try_on_images": [
    {"product": "red", "model": "front", "url": "/try-on-jobs/{id}/files/red__front.png"}
  ],
  "error": null
}
```

`try_on_images` 顺序：商品图外层、模特图内层。

### `GET /try-on-jobs/{id}/files/{filename}`

下载 `out/` 中的文件。非法文件名 400，任务不存在或文件不存在 404。

## 失败

- 创建时缺 `products` 或 `models`：422
- ingest 校验失败：任务 `failed`，`error` 为原因
- 某一对 `images.edit` 失败：整次任务 `failed`，不把已写出的文件当作成功结果返回
- 未知任务：404

## 测试

假 `RecordingEditor` 覆盖 ingest、图编排、HTTP。真实 `images.edit` 标 `@pytest.mark.integration`。

- ingest：空列表、非法后缀、合法 stem
- 图：2×2 共 4 次 edit，参考图顺序 `[模特, 商品]`，文件名 `{product}__{model}.png`，edit 抛错则 invoke 失败
- API：缺字段 422，2×2 成功可下载，未知任务 404
- 印花现有用例保持通过
- integration：1 商品图 + 1 模特图；无密钥或夹具则 skip。模特夹具 `tests/fixtures/model.png`（或 jpeg），可用 `TEST_MODEL_IMAGE` 覆盖

## 文件

- 新增：`build_try_on_graph`、`ingest_try_on`、`TRY_ON_PROMPT`、`TryOnState`
- 修改：`src/api/app.py`、`src/api/jobs.py`、`README.md`
- 测试：`tests/test_ingest.py`、`tests/test_graph.py`、`tests/test_api.py`、`tests/test_try_on_image.py`
