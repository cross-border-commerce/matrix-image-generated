"""真实换装生图：调用 images.edit，从路径读取商品图和模特图。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from product_shoot.nodes.image_edit import OpenAIImageEditor
from product_shoot.nodes.prompts import TRY_ON_PROMPT
from product_shoot.openai_client import get_openai_client

load_dotenv()

PRODUCT_IMAGE = Path(os.environ.get("TEST_PRODUCT_IMAGE", "tests/fixtures/realshot/white.jpeg"))
MODEL_IMAGE = Path(os.environ.get("TEST_MODEL_IMAGE", "tests/fixtures/reference/model1/model1_01.jpg"))
OUTPUT_DIR = Path("data/test_output")


def _has_api_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY"))


@pytest.mark.integration
@pytest.mark.skipif(not _has_api_key(), reason="未配置 OPENAI_API_KEY，跳过真实生图")
@pytest.mark.skipif(
    not PRODUCT_IMAGE.is_file() or not MODEL_IMAGE.is_file(),
    reason="缺少 tests/fixtures/realshot/white.jpeg 或 tests/fixtures/reference/model1/model1_01.jpg",
)
def test_try_on_editor_writes_image() -> None:
    """调用真实 images.edit：参考图顺序为 [模特, 商品]。"""
    assert "只替换服装" in TRY_ON_PROMPT
    assert "模特" in TRY_ON_PROMPT

    image_bytes = OpenAIImageEditor(get_openai_client()).edit(
        [MODEL_IMAGE, PRODUCT_IMAGE],
        TRY_ON_PROMPT,
    )

    assert len(image_bytes) > 1000
    assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n" or image_bytes[:2] == b"\xff\xd8"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUTPUT_DIR / "try_on.png"
    dest.write_bytes(image_bytes)
    assert dest.is_file()
