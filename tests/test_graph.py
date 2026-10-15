"""工作流：图节点只循环已配好的工作项（编辑器用假实现）。"""

from pathlib import Path

from product_shoot.graph import build_graph, build_try_on_graph
from product_shoot.nodes.prompts import TRY_ON_PROMPT, TRY_ON_PROMPT_WITH_PRINT
from tests.image_helpers import MINIMAL_PNG, write_png


class RecordingEditor:
    """记下每次生图调用的参考图和提示词。"""

    def __init__(self) -> None:
        self.calls: list[tuple[list[Path], str]] = []

    def edit(self, images: list[Path], prompt: str) -> bytes:
        self.calls.append((list(images), prompt))
        return MINIMAL_PNG


def test_graph_creates_one_image_per_generate_work_item(tmp_path: Path) -> None:
    """生图节点按工作项各出一张，参考图顺序为 [实拍, logo]。"""
    brand = write_png(tmp_path / "brand.png")
    mark = write_png(tmp_path / "mark.png")
    red = write_png(tmp_path / "red.png")
    blue = write_png(tmp_path / "blue.png")
    editor = RecordingEditor()

    graph = build_graph(editor=editor, output_dir=tmp_path / "out")
    result = graph.invoke(
        {
            "placement": "chest_center",
            "work_items": [
                {
                    "product_name": "red",
                    "logo_name": "brand",
                    "product_path": red,
                    "logo_path": brand,
                },
                {
                    "product_name": "red",
                    "logo_name": "mark",
                    "product_path": red,
                    "logo_path": mark,
                },
                {
                    "product_name": "blue",
                    "logo_name": "brand",
                    "product_path": blue,
                    "logo_path": brand,
                },
                {
                    "product_name": "blue",
                    "logo_name": "mark",
                    "product_path": blue,
                    "logo_path": mark,
                },
            ],
        }
    )

    images = result["product_images"]
    assert [(item["product_name"], item["logo_name"]) for item in images] == [
        ("red", "brand"),
        ("red", "mark"),
        ("blue", "brand"),
        ("blue", "mark"),
    ]
    assert all(Path(item["path"]).is_file() for item in images)
    assert [Path(item["path"]).name for item in images] == [
        "red__brand.png",
        "red__mark.png",
        "blue__brand.png",
        "blue__mark.png",
    ]
    assert [call[0] for call in editor.calls] == [
        [red, brand],
        [red, mark],
        [blue, brand],
        [blue, mark],
    ]
    assert all("胸前" in call[1] for call in editor.calls)
    assert all("{placement}" not in call[1] for call in editor.calls)


def test_try_on_graph_edits_each_work_item_with_grouped_product_photos(
    tmp_path: Path,
) -> None:
    """换装节点一次 edit 传入一张模特图和同一件商品的全部角度。"""
    red_front = write_png(tmp_path / "red-front.png")
    red_back = write_png(tmp_path / "red-back.png")
    blue = write_png(tmp_path / "blue.png")
    m1 = write_png(tmp_path / "m1.png")
    m2 = write_png(tmp_path / "m2.png")
    editor = RecordingEditor()

    graph = build_try_on_graph(editor=editor, output_dir=tmp_path / "out")
    result = graph.invoke(
        {
            "work_items": [
                {
                    "product_name": "red",
                    "model_name": "m1",
                    "product_paths": [red_front, red_back],
                    "model_path": m1,
                    "logo_name": None,
                    "logo_path": None,
                },
                {
                    "product_name": "blue",
                    "model_name": "m2",
                    "product_paths": [blue],
                    "model_path": m2,
                    "logo_name": None,
                    "logo_path": None,
                },
            ]
        }
    )

    images = result["try_on_images"]
    assert [(item["product_name"], item["model_name"]) for item in images] == [
        ("red", "m1"),
        ("blue", "m2"),
    ]
    assert [Path(item["path"]).name for item in images] == [
        "red__m1.png",
        "blue__m2.png",
    ]
    assert all(Path(item["path"]).is_file() for item in images)
    assert [call[0] for call in editor.calls] == [
        [m1, red_front, red_back],
        [m2, blue],
    ]
    assert all(call[1] == TRY_ON_PROMPT for call in editor.calls)
    assert "只替换服装" in TRY_ON_PROMPT
    assert "模特" in TRY_ON_PROMPT


def test_try_on_graph_appends_print_reference_when_work_item_has_logo(
    tmp_path: Path,
) -> None:
    """有印花的换装工作项把 logo 放在参考图最后。"""
    product = write_png(tmp_path / "white.png")
    model = write_png(tmp_path / "m1.png")
    brand = write_png(tmp_path / "brand.png")
    editor = RecordingEditor()

    graph = build_try_on_graph(editor=editor, output_dir=tmp_path / "out")
    result = graph.invoke(
        {
            "work_items": [
                {
                    "product_name": "white",
                    "model_name": "m1",
                    "product_paths": [product],
                    "model_path": model,
                    "logo_name": "brand",
                    "logo_path": brand,
                }
            ]
        }
    )

    images = result["try_on_images"]
    assert [Path(item["path"]).name for item in images] == ["white__m1__brand.png"]
    assert editor.calls[0][0] == [model, product, brand]
    assert editor.calls[0][1] == TRY_ON_PROMPT_WITH_PRINT
    assert "印花" in TRY_ON_PROMPT_WITH_PRINT
