# matrix-image-generated

印花：上传印花 logo 和工厂纯色实拍图，先把商品图收成「一件商品」，再和每张印花配成工作项，生成带 logo 的商品图。

换装：独立接口上传印花、商品成衣图和模特参考图。组合按印花 × 参考图展开，每格再选一件商品。印花必填，输出张数 = 印花数 × 参考图数。

商品图如何收成一件（印花不参与）：

- 上传文件名在同一子目录里的，算同一件（例如 `white/front.jpeg` 和 `white/back.jpeg`）
- 去掉 正面 / 背面 / 侧面 / 细节 / 局部 / front / back / side / detail 后词干相同的，也算同一件（例如 `白色-正面.jpeg` 和 `白色-背面.jpeg` → 一件「白色」）

换装组合：印花第一维，参考图第二维。

- 每个 logo 下，每张参考图一行，默认同下标商品（参考图多于商品时循环商品）
- 可用 `apparelColorAssignments` 改某一格配哪件。扁平 JSON 为参考图 stem → 商品组 id（对所有印花生效）；嵌套 JSON 为印花 stem → { 参考图 stem → 商品组 id }
- 商品再多也不会循环参考图去凑件数

输出张数 = 印花数 × 参考图数。换装时同一件的多角度图会一起作为参考，印花作为最后一张参考图。

编排用 LangGraph，生图用 OpenAI `images.edit`。分组和配对在接口里完成，图节点只循环已经配好的工作项。印花生图提示词由开发者写模板，运行时只替换 `{placement}` 等变量。换装提示词固定，不插变量。

## 环境与依赖（uv）

本项目用 [uv](https://docs.astral.sh/uv/) 管理虚拟环境和依赖。未安装时：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

在项目根目录执行：

```bash
uv sync --extra dev
```

会生成/更新 `uv.lock` 和 `.venv`，并安装运行依赖与测试依赖。之后用 `uv run` 执行命令，不必先 `source .venv/bin/activate`。

常用命令：

```bash
# 按 lockfile 安装
uv sync --extra dev

# 增加依赖
uv add fastapi
uv add --dev pytest

# 升级 lockfile 中的包
uv lock --upgrade
```

## 环境变量

后端从项目根目录的 `.env` 读配置（`python-dotenv` 在创建 OpenAI 客户端时 `load_dotenv()`）。可先复制示例再改：

```bash
cp .env.example .env
```

`.env` 示例：

```
OPENAI_BASE_URL=https://www.guxiaohong666.com/v1
OPENAI_API_KEY=sk-...
```

| 变量 | 是否必填 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | 生图必填 | OpenAI 兼容接口的密钥。也可用 `API_KEY` |
| `OPENAI_BASE_URL` | 否 | 自定义 API 根地址。也可用 `OPENAI_API_BASE_URL` 或 `API_BASE_URL`。不设则走官方默认地址 |
| `DATA_DIR` | 否 | 任务文件与生成图的存储目录，默认 `data` |
| `TEST_PRODUCT_IMAGE` | 否 | 真实生图测试用的实拍路径 |
| `TEST_LOGO_IMAGE` | 否 | 真实生图测试用的印花路径 |
| `TEST_MODEL_IMAGE` | 否 | 真实换装测试用的模特路径 |

前端开发不需要单独的 `.env`。`frontend/vite.config.ts` 会把 `/jobs`、`/try-on-jobs` 代理到 `http://127.0.0.1:8000`。

不要把填好密钥的 `.env` 提交进 git。

## 启动

需要两个进程：后端提供接口和生图，前端提供页面。

**1. 后端**（项目根目录，默认 http://127.0.0.1:8000 ）

```bash
uv sync --extra dev
uv run uvicorn api.app:create_default_app --factory --app-dir src --host 0.0.0.0 --port 8000
```

**2. 前端**（另开一个终端）

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5173 ，上传印花、实拍、参考模特，在配对卡片里配置后生成。

**生产**

```bash
cd frontend
npm install
npm run build
```

回到项目根目录启动后端。若存在 `frontend/dist`，FastAPI 会在同域托管页面，直接访问 http://127.0.0.1:8000 即可，不必再跑 Vite。

## API

`POST /jobs`（multipart）

- `logos`：1 张或多张印花 logo（png / jpg / webp）
- `products`：1 张或多张纯色实拍
- `placement`：可选，默认 `chest_center`

一次任务先把实拍收成商品件，再按「一件商品 × 一张印花」生成商品图。同一件的多角度只用组内第一张实拍去贴印花。

`GET /jobs/{id}` 查询状态和商品图 URL。

`GET /jobs/{id}/files/{filename}` 下载生成图。

`POST /try-on-jobs`（multipart）

- `products`：1 张或多张商品成衣图（png / jpg / webp）
- `models`：1 张或多张模特参考图
- `logos`：1 张或多张印花，必填；输出张数 = 印花数 × 参考图数
- `apparelColorAssignments`：可选 JSON。扁平：参考图 stem → 商品组 id；嵌套：印花 stem → { 参考图 stem → 商品组 id }

一次任务先把实拍收成商品件，再按印花 × 参考图展开工作项。换装 `images.edit` 参考图为 `[模特, …同一件的全部角度, 印花]`。

`GET /try-on-jobs/{id}` 查询状态和换装图 URL。

`GET /try-on-jobs/{id}/files/{filename}` 下载换装图。

示例：

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -F logos=@brand.png \
  -F logos=@mark.png \
  -F products=@red.png \
  -F products=@blue.png \
  -F placement=chest_center

curl -X POST http://127.0.0.1:8000/try-on-jobs \
  -F logos=@brand.png \
  -F products=@white-front.png \
  -F products=@white-back.png \
  -F products=@black.png \
  -F models=@m1.png \
  -F models=@m2.png \
  -F 'apparelColorAssignments={"m1":"white","m2":"black"}'
```

## 测试

```bash
# 单元测试（不含真实生图）
uv run pytest -m "not integration"

# 全部测试，含真实生图（需配置 OPENAI_API_KEY）
uv run pytest
```

真实生图会读取本地文件（不限制宽高）：

- `tests/fixtures/realshot/`：工厂纯色实拍 / 商品成衣图
- `tests/fixtures/logo/`：印花 logo
- `tests/fixtures/reference/`：模特参考图（换装 integration 用）

也可用环境变量 `TEST_PRODUCT_IMAGE`、`TEST_LOGO_IMAGE`、`TEST_MODEL_IMAGE` 指向其它路径。缺少文件时该用例会 skip。

印花结果写在 `data/test_output/generated_product.png`，换装结果写在 `data/test_output/try_on.png`。
