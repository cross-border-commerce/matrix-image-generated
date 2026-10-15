# matrix-image-generated

印花：上传印花 logo 和工厂纯色实拍图，先把商品图收成「一件商品」，再和每张印花配成工作项，生成带 logo 的商品图。

换装：独立接口上传商品成衣图和模特参考图，同样先收成一件再和模特配对，把衣服穿到模特身上。可选再带印花，输出张数 = 配对数 × 印花张数。

商品图如何收成一件（印花不参与）：

- 上传文件名在同一子目录里的，算同一件（例如 `white/front.jpeg` 和 `white/back.jpeg`）
- 去掉 正面 / 背面 / 侧面 / 细节 / 局部 / front / back / side / detail 后词干相同的，也算同一件（例如 `白色-正面.jpeg` 和 `白色-背面.jpeg` → 一件「白色」）

换装配对：每张参考模特图只配一件商品。

- 参考模特图 ≥ 商品件数：第 1 张模特配第 1 件，第 2 张配第 2 件；商品不够从头循环。可用表单字段 `apparelColorAssignments`（JSON：模特文件名 stem → 商品组 id）改某一张配哪件
- 商品件数 > 参考模特图：忽略手动指定，模特图循环，保证每件商品都有一张参考模特图

无印花时输出 = 配对数；有印花时输出 = 配对数 × 印花张数。换装时同一件的多角度图会一起作为参考。

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

在项目根目录 `.env` 中填写：

```
OPENAI_API_BASE_URL=https://www.guxiaohong666.com/v1
OPENAI_API_KEY=sk-...
```

## 运行

```bash
uv run uvicorn api.app:create_default_app --factory --app-dir src --host 0.0.0.0 --port 8000
```

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
- `logos`：可选，1 张或多张印花；出现时输出张数 = 配对数 × 印花张数
- `apparelColorAssignments`：可选 JSON 对象，模特 stem → 商品组 id。仅当模特数不少于商品件数时生效

一次任务先分组再按上面的规则配对。换装 `images.edit` 参考图为 `[模特, …同一件的全部角度]`，有印花时再追加 logo。

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
