"""商品图分组、模特配对、工作项展开。"""

from pathlib import Path

from product_shoot.pairing import (
    expand_generate_work_items,
    expand_try_on_work_items,
    group_products,
    pair_models,
)
from tests.image_helpers import write_png


def _photo(path: Path, name: str | None = None) -> dict:
    return {"name": name or path.name, "photo_path": path}


def test_group_products_merges_view_suffix_stems(tmp_path: Path) -> None:
    """去掉正面/背面等词后词干相同的，算同一件。"""
    front = write_png(tmp_path / "白色-正面.jpeg")
    back = write_png(tmp_path / "白色-背面.jpeg")
    black = write_png(tmp_path / "黑色.jpeg")

    groups = group_products(
        [
            _photo(front, "白色-正面.jpeg"),
            _photo(back, "白色-背面.jpeg"),
            _photo(black, "黑色.jpeg"),
        ]
    )

    assert [group["id"] for group in groups] == ["白色", "黑色"]
    assert [item["photo_path"] for item in groups[0]["photos"]] == [front, back]
    assert [item["photo_path"] for item in groups[1]["photos"]] == [black]


def test_group_products_merges_english_view_suffixes(tmp_path: Path) -> None:
    """front/back/side/detail 与中文视角词同样去掉后再比词干。"""
    front = write_png(tmp_path / "white-front.png")
    back = write_png(tmp_path / "white-back.png")
    side = write_png(tmp_path / "navy_side.png")
    detail = write_png(tmp_path / "navy-detail.png")

    groups = group_products(
        [
            _photo(front, "white-front.png"),
            _photo(back, "white-back.png"),
            _photo(side, "navy_side.png"),
            _photo(detail, "navy-detail.png"),
        ]
    )

    assert [group["id"] for group in groups] == ["white", "navy"]
    assert [item["photo_path"] for item in groups[0]["photos"]] == [front, back]
    assert [item["photo_path"] for item in groups[1]["photos"]] == [side, detail]


def test_group_products_merges_same_logical_directory(tmp_path: Path) -> None:
    """逻辑路径在同一子目录里的，算同一件。"""
    front = write_png(tmp_path / "front.jpeg")
    back = write_png(tmp_path / "back.jpeg")
    other = write_png(tmp_path / "red.jpeg")

    groups = group_products(
        [
            _photo(front, "white/front.jpeg"),
            _photo(back, "white/back.jpeg"),
            _photo(other, "red.jpeg"),
        ]
    )

    assert [group["id"] for group in groups] == ["white", "red"]
    assert [item["photo_path"] for item in groups[0]["photos"]] == [front, back]


def test_group_products_keeps_flat_names_in_same_folder_separate(
    tmp_path: Path,
) -> None:
    """扁平文件名只靠词干分组，不因落在同一存储目录而合成一件。"""
    red = write_png(tmp_path / "red.png")
    blue = write_png(tmp_path / "blue.png")

    groups = group_products([_photo(red, "red.png"), _photo(blue, "blue.png")])

    assert [group["id"] for group in groups] == ["red", "blue"]


def test_group_products_keeps_different_stems_in_shared_folder_separate(
    tmp_path: Path,
) -> None:
    """同一上传文件夹里词干不同的成衣，仍是多件，不因同目录收成一件。"""
    white = write_png(tmp_path / "white.jpeg")
    block = write_png(tmp_path / "block.jpeg")
    gray = write_png(tmp_path / "light_gray.jpeg")

    groups = group_products(
        [
            _photo(white, "fixtures/realshot/white.jpeg"),
            _photo(block, "fixtures/realshot/block.jpeg"),
            _photo(gray, "fixtures/realshot/light_gray.jpeg"),
        ]
    )

    assert [group["id"] for group in groups] == ["white", "block", "light-gray"]


def test_pair_models_matches_by_index_and_cycles_products() -> None:
    """模特数不少于商品件数时，按下标配对，商品不够从头循环。"""
    models = [
        {"name": "m1", "photo_path": Path("m1.jpg")},
        {"name": "m2", "photo_path": Path("m2.jpg")},
        {"name": "m3", "photo_path": Path("m3.jpg")},
    ]
    groups = [
        {"id": "white", "photos": [{"name": "white.png", "photo_path": Path("white.png")}]},
        {"id": "black", "photos": [{"name": "black.png", "photo_path": Path("black.png")}]},
    ]

    pairs = pair_models(models, groups)

    assert [(model["name"], group["id"]) for model, group in pairs] == [
        ("m1", "white"),
        ("m2", "black"),
        ("m3", "white"),
    ]


def test_pair_models_keeps_one_row_per_reference_when_more_products() -> None:
    """组合按参考图展开：商品再多也是一张参考图一行，指定仍然生效。"""
    models = [
        {"name": "m1", "photo_path": Path("m1.jpg")},
        {"name": "m2", "photo_path": Path("m2.jpg")},
    ]
    groups = [
        {"id": "white", "photos": []},
        {"id": "black", "photos": []},
        {"id": "navy", "photos": []},
    ]
    assignments = {"m1": "navy", "m2": "black"}

    pairs = pair_models(models, groups, assignments=assignments)

    assert [(model["name"], group["id"]) for model, group in pairs] == [
        ("m1", "navy"),
        ("m2", "black"),
    ]


def test_pair_models_uses_assignments_when_models_cover_products() -> None:
    """模特数不少于件数时，apparelColorAssignments 覆盖默认下标配对。"""
    models = [
        {"name": "m1", "photo_path": Path("m1.jpg")},
        {"name": "m2", "photo_path": Path("m2.jpg")},
    ]
    groups = [
        {"id": "white", "photos": []},
        {"id": "black", "photos": []},
    ]

    pairs = pair_models(models, groups, assignments={"m1": "black", "m2": "white"})

    assert [(model["name"], group["id"]) for model, group in pairs] == [
        ("m1", "black"),
        ("m2", "white"),
    ]


def test_expand_generate_work_items_is_group_by_logo() -> None:
    """生图工作项是一件商品 × 一张印花，商品组用第一张实拍。"""
    front = Path("white-front.png")
    back = Path("white-back.png")
    black = Path("black.png")
    brand = {"name": "brand", "photo_path": Path("brand.png")}
    mark = {"name": "mark", "photo_path": Path("mark.png")}
    groups = [
        {
            "id": "white",
            "photos": [
                {"name": "white-front.png", "photo_path": front},
                {"name": "white-back.png", "photo_path": back},
            ],
        },
        {"id": "black", "photos": [{"name": "black.png", "photo_path": black}]},
    ]

    items = expand_generate_work_items(groups, [brand, mark])

    assert [
        (item["product_name"], item["logo_name"], item["product_path"], item["logo_path"])
        for item in items
    ] == [
        ("white", "brand", front, Path("brand.png")),
        ("white", "mark", front, Path("mark.png")),
        ("black", "brand", black, Path("brand.png")),
        ("black", "mark", black, Path("mark.png")),
    ]


def test_expand_try_on_work_items_is_logo_then_reference() -> None:
    """工作项按印花第一维、参考图第二维展开。"""
    models = [
        {"name": "m1", "photo_path": Path("m1.jpg")},
        {"name": "m2", "photo_path": Path("m2.jpg")},
    ]
    groups = [
        {
            "id": "white",
            "photos": [
                {"name": "white-front.png", "photo_path": Path("front.png")},
                {"name": "white-back.png", "photo_path": Path("back.png")},
            ],
        },
        {"id": "black", "photos": [{"name": "black.png", "photo_path": Path("black.png")}]},
    ]
    logos = [
        {"name": "brand", "photo_path": Path("brand.png")},
        {"name": "mark", "photo_path": Path("mark.png")},
    ]

    items = expand_try_on_work_items(logos, models, groups)
    assert [
        (item["logo_name"], item["model_name"], item["product_name"])
        for item in items
    ] == [
        ("brand", "m1", "white"),
        ("brand", "m2", "black"),
        ("mark", "m1", "white"),
        ("mark", "m2", "black"),
    ]
    assert items[0]["product_paths"] == [Path("front.png"), Path("back.png")]
    assert items[0]["logo_path"] == Path("brand.png")


def test_expand_try_on_work_items_assignments_are_per_logo() -> None:
    """每个 logo 下可为同一张参考图指定不同商品。"""
    models = [{"name": "m1", "photo_path": Path("m1.jpg")}]
    groups = [
        {"id": "white", "photos": [{"name": "white.png", "photo_path": Path("white.png")}]},
        {"id": "black", "photos": [{"name": "black.png", "photo_path": Path("black.png")}]},
    ]
    logos = [
        {"name": "brand", "photo_path": Path("brand.png")},
        {"name": "mark", "photo_path": Path("mark.png")},
    ]
    items = expand_try_on_work_items(
        logos,
        models,
        groups,
        assignments={"brand": {"m1": "black"}, "mark": {"m1": "white"}},
    )
    assert [
        (item["logo_name"], item["model_name"], item["product_name"])
        for item in items
    ] == [
        ("brand", "m1", "black"),
        ("mark", "m1", "white"),
    ]
