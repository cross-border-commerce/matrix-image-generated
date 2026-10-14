"""生图：解析接口返回，并调用真实 images.edit。"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from dotenv import load_dotenv

from product_shoot.nodes.image_edit import OpenAIImageEditor
from product_shoot.nodes.prompts import render_image_prompt
from product_shoot.openai_client import get_openai_client
from tests.image_helpers import MINIMAL_PNG, write_color_png, write_png

load_dotenv()

# 生成图落到 data/，方便本地打开查看
OUTPUT_DIR = Path("data/test_output")


def _has_api_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY"))


def test_image_editor_downloads_when_response_has_url(tmp_path: Path) -> None:
    """部分网关只返回 url、不返回 b64_json，需要把图下载下来。"""
    product = write_png(tmp_path / "product.png")
    logo = write_png(tmp_path / "logo.png")

    class FakeImages:
        def edit(self, **kwargs):
            return SimpleNamespace(
                data=[SimpleNamespace(b64_json=None, url="https://example.com/out.png")]
            )

    downloaded: list[str] = []

    def fake_download(url: str) -> bytes:
        downloaded.append(url)
        return MINIMAL_PNG

    result = OpenAIImageEditor(
        SimpleNamespace(images=FakeImages()),
        download=fake_download,
    ).edit([product, logo], "贴 logo")

    assert result == MINIMAL_PNG
    assert downloaded == ["https://example.com/out.png"]


@pytest.mark.integration
@pytest.mark.skipif(not _has_api_key(), reason="未配置 OPENAI_API_KEY，跳过真实生图")
def test_edit_applies_logo_to_solid_product_photo() -> None:
    """调用 images.edit：参考图为 [实拍, logo]，提示词填入胸前位置。"""
    work = OUTPUT_DIR
    work.mkdir(parents=True, exist_ok=True)

    # 蓝色块模拟工厂纯色实拍，红色块模拟印花 logo（接口一般要求图不能太小）
    product = write_color_png(work / "product.png", 512, 512, (30, 90, 180))
    logo = write_color_png(work / "logo.png", 128, 128, (200, 40, 40))

    prompt = render_image_prompt("chest_center")
    assert "胸前" in prompt
    assert "{placement}" not in prompt

    image_bytes = OpenAIImageEditor(get_openai_client()).edit(
        [product, logo],
        prompt,
    )

    assert len(image_bytes) > 1000
    assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n" or image_bytes[:2] == b"\xff\xd8"

    dest = work / "generated_product.png"
    dest.write_bytes(image_bytes)
    assert dest.is_file()
