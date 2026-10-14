# matrix-image-generated

印花：上传印花 logo 和工厂纯色实拍图，按实拍 × 印花全组合生成带 logo 的商品图。

换装：独立接口上传商品成衣图和模特参考图，把衣服穿到模特身上。

编排用 LangGraph，生图用 OpenAI `images.edit`。印花生图提示词由开发者写模板，运行时只替换 `{placement}` 等变量。换装提示词固定，不插变量。

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

一次任务对实拍 × 印花做全组合，每对生成一张商品图。

`GET /jobs/{id}` 查询状态和商品图 URL。

`GET /jobs/{id}/files/{filename}` 下载生成图。

`POST /try-on-jobs`（multipart）

- `products`：1 张或多张商品成衣图（png / jpg / webp）
- `models`：1 张或多张模特参考图

一次任务对商品图 × 模特图做全组合，每对生成一张换装图。

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
  -F products=@red.png \
  -F products=@blue.png \
  -F models=@front.png \
  -F models=@side.png
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
