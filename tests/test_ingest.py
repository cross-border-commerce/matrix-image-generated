"""上传素材校验：logo 和纯色实拍必须存在且格式合法。"""

from pathlib import Path

import pytest

from product_shoot.nodes.ingest import IngestError, ingest, ingest_try_on
from tests.image_helpers import write_png


def test_ingest_rejects_empty_product_list(tmp_path: Path) -> None:
    """没有实拍图时拒绝入库。"""
    logo = write_png(tmp_path / "logo.png")

    with pytest.raises(IngestError, match="at least one product"):
        ingest(logos=[logo], products=[])


def test_ingest_rejects_empty_logo_list(tmp_path: Path) -> None:
    """没有印花图时拒绝入库。"""
    product = write_png(tmp_path / "red.png")

    with pytest.raises(IngestError, match="at least one logo"):
        ingest(logos=[], products=[product])


def test_ingest_rejects_unsupported_logo_type(tmp_path: Path) -> None:
    """logo 不是 png/jpg/webp 时拒绝。"""
    logo = tmp_path / "logo.gif"
    logo.write_bytes(b"gif")
    product = write_png(tmp_path / "red.png")

    with pytest.raises(IngestError, match="unsupported"):
        ingest(logos=[logo], products=[product])


def test_ingest_uses_default_placement_and_keeps_names(tmp_path: Path) -> None:
    """默认贴标位置为胸前，印花名和实拍名取文件名。"""
    brand = write_png(tmp_path / "brand.png")
    mark = write_png(tmp_path / "mark.png")
    red = write_png(tmp_path / "red.png")
    blue = write_png(tmp_path / "blue.jpg")

    state = ingest(logos=[brand, mark], products=[red, blue])

    assert state["placement"] == "chest_center"
    assert [item["name"] for item in state["logos"]] == ["brand", "mark"]
    assert [item["photo_path"] for item in state["logos"]] == [brand, mark]
    assert [item["name"] for item in state["products"]] == ["red", "blue"]
    assert [item["photo_path"] for item in state["products"]] == [red, blue]


def test_ingest_try_on_rejects_empty_product_list(tmp_path: Path) -> None:
    """没有商品图时拒绝入库。"""
    model = write_png(tmp_path / "front.png")

    with pytest.raises(IngestError, match="at least one product"):
        ingest_try_on(products=[], models=[model])


def test_ingest_try_on_rejects_empty_model_list(tmp_path: Path) -> None:
    """没有模特图时拒绝入库。"""
    product = write_png(tmp_path / "red.png")

    with pytest.raises(IngestError, match="at least one model"):
        ingest_try_on(products=[product], models=[])


def test_ingest_try_on_rejects_unsupported_model_type(tmp_path: Path) -> None:
    """模特图不是 png/jpg/webp 时拒绝。"""
    product = write_png(tmp_path / "red.png")
    model = tmp_path / "front.gif"
    model.write_bytes(b"gif")

    with pytest.raises(IngestError, match="unsupported"):
        ingest_try_on(products=[product], models=[model])


def test_ingest_try_on_keeps_product_and_model_names(tmp_path: Path) -> None:
    """商品名和模特名取文件名。"""
    red = write_png(tmp_path / "red.png")
    blue = write_png(tmp_path / "blue.jpg")
    front = write_png(tmp_path / "front.png")

    state = ingest_try_on(products=[red, blue], models=[front])

    assert [item["name"] for item in state["products"]] == ["red", "blue"]
    assert [item["name"] for item in state["models"]] == ["front"]
    assert [item["photo_path"] for item in state["products"]] == [red, blue]
    assert [item["photo_path"] for item in state["models"]] == [front]
