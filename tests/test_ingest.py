"""上传素材校验：logo 和纯色实拍必须存在且格式合法。"""

from pathlib import Path

import pytest

from product_shoot.nodes.ingest import IngestError, ingest
from tests.image_helpers import write_png


def test_ingest_rejects_empty_product_list(tmp_path: Path) -> None:
    """没有实拍图时拒绝入库。"""
    logo = write_png(tmp_path / "logo.png")

    with pytest.raises(IngestError, match="at least one"):
        ingest(logo=logo, products=[])


def test_ingest_rejects_unsupported_logo_type(tmp_path: Path) -> None:
    """logo 不是 png/jpg/webp 时拒绝。"""
    logo = tmp_path / "logo.gif"
    logo.write_bytes(b"gif")
    product = write_png(tmp_path / "red.png")

    with pytest.raises(IngestError, match="unsupported"):
        ingest(logo=logo, products=[product])


def test_ingest_uses_default_placement_and_keeps_product_names(tmp_path: Path) -> None:
    """默认贴标位置为胸前，商品名取文件名。"""
    logo = write_png(tmp_path / "logo.png")
    red = write_png(tmp_path / "red.png")
    blue = write_png(tmp_path / "blue.jpg")

    state = ingest(logo=logo, products=[red, blue])

    assert state["logo_path"] == logo
    assert state["placement"] == "chest_center"
    assert [item["name"] for item in state["products"]] == ["red", "blue"]
    assert [item["photo_path"] for item in state["products"]] == [red, blue]
