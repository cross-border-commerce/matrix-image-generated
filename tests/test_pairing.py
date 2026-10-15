"""商品图分组、模特配对、工作项展开。"""

from pathlib import Path

from product_shoot.pairing import (
    expand_generate_work_items,
    expand_try_on_work_items,
    group_models,
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


def test_group_models_uses_each_subdirectory_as_a_group(tmp_path: Path) -> None:
    """每个子目录是一组参考模特图。"""
    a1 = write_png(tmp_path / "a1.jpg")
    a2 = write_png(tmp_path / "a2.jpg")
    b1 = write_png(tmp_path / "b1.jpg")

    groups = group_models(
        [
            _photo(a1, "reference/model1/a1.jpg"),
            _photo(a2, "reference/model1/a2.jpg"),
            _photo(b1, "reference/model2/b1.jpg"),
        ]
    )

    assert [group["id"] for group in groups] == ["model1", "model2"]
    assert [item["photo_path"] for item in groups[0]["photos"]] == [a1, a2]
    assert [item["photo_path"] for item in groups[1]["photos"]] == [b1]


def test_group_models_treats_flat_images_as_one_group(tmp_path: Path) -> None:
    """文件夹里没有子目录、全是图片时，全部算一组。"""
    m1 = write_png(tmp_path / "m1.png")
    m2 = write_png(tmp_path / "m2.png")

    groups = group_models([_photo(m1, "m1.png"), _photo(m2, "m2.png")])

    assert [group["id"] for group in groups] == ["models"]
    assert [item["photo_path"] for item in groups[0]["photos"]] == [m1, m2]


def test_group_models_treats_shared_parent_folder_as_one_group(tmp_path: Path) -> None:
    """同一层目录下没有再分子目录时，该目录内全部算一组。"""
    m1 = write_png(tmp_path / "m1.png")
    m2 = write_png(tmp_path / "m2.png")

    groups = group_models(
        [
            _photo(m1, "reference/m1.png"),
            _photo(m2, "reference/m2.png"),
        ]
    )

    assert [group["id"] for group in groups] == ["reference"]
    assert [item["photo_path"] for item in groups[0]["photos"]] == [m1, m2]


def test_pair_models_cycles_products_across_photos_in_a_group() -> None:
    """一组里每张参考图配一件商品，商品不够从头循环。"""
    photos = [
        {"name": "a1.jpg", "photo_path": Path("a1.jpg")},
        {"name": "a2.jpg", "photo_path": Path("a2.jpg")},
        {"name": "a3.jpg", "photo_path": Path("a3.jpg")},
    ]
    groups = [
        {"id": "A", "photos": []},
        {"id": "B", "photos": []},
    ]

    pairs = pair_models(photos, groups)

    assert [(model["name"], group["id"]) for model, group in pairs] == [
        ("a1.jpg", "A"),
        ("a2.jpg", "B"),
        ("a3.jpg", "A"),
    ]


def test_pair_models_keeps_one_row_per_photo_when_more_products() -> None:
    """商品再多也按组内参考图张数展开。"""
    photos = [
        {"name": "a1.jpg", "photo_path": Path("a1.jpg")},
        {"name": "a2.jpg", "photo_path": Path("a2.jpg")},
    ]
    groups = [
        {"id": "A", "photos": []},
        {"id": "B", "photos": []},
        {"id": "C", "photos": []},
    ]

    pairs = pair_models(photos, groups)

    assert [(model["name"], group["id"]) for model, group in pairs] == [
        ("a1.jpg", "A"),
        ("a2.jpg", "B"),
    ]


def test_pair_models_uses_row_assignments() -> None:
    """指定覆盖组内某一张参考图默认配对的商品。"""
    photos = [
        {"name": "a1.jpg", "photo_path": Path("a1.jpg")},
        {"name": "a2.jpg", "photo_path": Path("a2.jpg")},
    ]
    groups = [
        {"id": "A", "photos": []},
        {"id": "B", "photos": []},
        {"id": "C", "photos": []},
    ]

    pairs = pair_models(photos, groups, assignments={"0": "C"})

    assert [(model["name"], group["id"]) for model, group in pairs] == [
        ("a1.jpg", "C"),
        ("a2.jpg", "B"),
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


def test_expand_try_on_work_items_one_logo_one_model_group() -> None:
    """一个 logo 配一组参考图，组内每张参考图配不同商品。"""
    model_groups = [
        {
            "id": "a",
            "photos": [
                {"name": "a/a1.jpg", "photo_path": Path("a1.jpg")},
                {"name": "a/a2.jpg", "photo_path": Path("a2.jpg")},
            ],
        },
        {"id": "b", "photos": [{"name": "b/b1.jpg", "photo_path": Path("b1.jpg")}]},
    ]
    groups = [
        {
            "id": "A",
            "photos": [
                {"name": "white-front.png", "photo_path": Path("front.png")},
                {"name": "white-back.png", "photo_path": Path("back.png")},
            ],
        },
        {"id": "B", "photos": [{"name": "black.png", "photo_path": Path("black.png")}]},
        {"id": "C", "photos": [{"name": "navy.png", "photo_path": Path("navy.png")}]},
    ]
    logos = [
        {"name": "brand", "photo_path": Path("brand.png")},
        {"name": "mark", "photo_path": Path("mark.png")},
    ]

    items = expand_try_on_work_items(logos, model_groups, groups)
    assert [
        (item["logo_name"], item["model_name"], item["product_name"])
        for item in items
    ] == [
        ("brand", "a1", "A"),
        ("brand", "a2", "B"),
        ("mark", "b1", "A"),
    ]
    assert items[0]["product_paths"] == [Path("front.png"), Path("back.png")]
    assert items[0]["model_path"] == Path("a1.jpg")
    assert items[0]["logo_path"] == Path("brand.png")


def test_expand_try_on_work_items_cycles_model_groups_across_logos() -> None:
    """logo 多于模特组时，模特组从头循环。"""
    model_groups = [
        {"id": "a", "photos": [{"name": "a1.jpg", "photo_path": Path("a1.jpg")}]},
        {"id": "b", "photos": [{"name": "b1.jpg", "photo_path": Path("b1.jpg")}]},
    ]
    groups = [
        {"id": "A", "photos": [{"name": "A.png", "photo_path": Path("A.png")}]},
    ]
    logos = [
        {"name": "brand", "photo_path": Path("brand.png")},
        {"name": "mark", "photo_path": Path("mark.png")},
        {"name": "extra", "photo_path": Path("extra.png")},
    ]

    items = expand_try_on_work_items(logos, model_groups, groups)
    assert [
        (item["logo_name"], item["model_name"], item["product_name"])
        for item in items
    ] == [
        ("brand", "a1", "A"),
        ("mark", "b1", "A"),
        ("extra", "a1", "A"),
    ]


def test_expand_try_on_work_items_assignments_are_per_logo() -> None:
    """每个 logo 下可为组内某一张参考图指定不同商品。"""
    model_groups = [
        {
            "id": "a",
            "photos": [
                {"name": "a1.jpg", "photo_path": Path("a1.jpg")},
                {"name": "a2.jpg", "photo_path": Path("a2.jpg")},
            ],
        },
        {"id": "b", "photos": [{"name": "b1.jpg", "photo_path": Path("b1.jpg")}]},
    ]
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
        model_groups,
        groups,
        assignments={"brand": {"0": "black"}, "mark": {"0": "white"}},
    )
    assert [
        (item["logo_name"], item["model_name"], item["product_name"])
        for item in items
    ] == [
        ("brand", "a1", "black"),
        ("brand", "a2", "black"),
        ("mark", "b1", "white"),
    ]
