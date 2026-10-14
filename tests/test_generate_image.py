"""真实生图接口测试：调用 images.edit，从路径读取实拍和 logo。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from product_shoot.nodes.image_edit import OpenAIImageEditor
from product_shoot.nodes.prompts import render_image_prompt
from product_shoot.openai_client import get_openai_client

load_dotenv()

# 纯色实拍、印花 logo 从路径读取，不限制宽高；生成图写到 data/ 方便查看
PRODUCT_IMAGE = Path(os.environ.get("TEST_PRODUCT_IMAGE", "tests/fixtures/product.jpeg"))
LOGO_IMAGE = Path(os.environ.get("TEST_LOGO_IMAGE", "tests/fixtures/logo.png"))
OUTPUT_DIR = Path("data/test_output")


def _has_api_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY"))


@pytest.mark.integration
@pytest.mark.skipif(not _has_api_key(), reason="未配置 OPENAI_API_KEY，跳过真实生图")
@pytest.mark.skipif(
    not PRODUCT_IMAGE.is_file() or not LOGO_IMAGE.is_file(),
    reason="缺少 tests/fixtures/product.png 或 tests/fixtures/logo.png",
)
def test_image_editor_downloads_when_response_has_url() -> None:
    """调用真实 images.edit：参考图为路径中的实拍和 logo。网关返回 url 时把图下载下来。"""
    prompt = render_image_prompt("chest_center")
    assert "胸前" in prompt
    assert "{placement}" not in prompt

    image_bytes = OpenAIImageEditor(get_openai_client()).edit(
        [PRODUCT_IMAGE, LOGO_IMAGE],
        prompt,
    )

    assert len(image_bytes) > 1000
    assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n" or image_bytes[:2] == b"\xff\xd8"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUTPUT_DIR / "generated_product.png"
    dest.write_bytes(image_bytes)
    assert dest.is_file()
