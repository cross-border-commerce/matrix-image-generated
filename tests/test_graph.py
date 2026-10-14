"""工作流：每种颜色的实拍各生成一张商品图（编辑器用假实现）。"""

from pathlib import Path

from product_shoot.graph import build_graph, build_try_on_graph
from product_shoot.nodes.prompts import TRY_ON_PROMPT
from tests.image_helpers import MINIMAL_PNG, write_png


class RecordingEditor:
    """记下每次生图调用的参考图和提示词。"""

    def __init__(self) -> None:
        self.calls: list[tuple[list[Path], str]] = []

    def edit(self, images: list[Path], prompt: str) -> bytes:
        self.calls.append((list(images), prompt))
        return MINIMAL_PNG


def test_graph_creates_one_image_per_product_logo_pair(tmp_path: Path) -> None:
    """两张实拍 × 两张印花应产出四张图，参考图顺序为 [实拍, logo]。"""
    brand = write_png(tmp_path / "brand.png")
    mark = write_png(tmp_path / "mark.png")
    red = write_png(tmp_path / "red.png")
    blue = write_png(tmp_path / "blue.png")
    editor = RecordingEditor()

    graph = build_graph(editor=editor, output_dir=tmp_path / "out")
    result = graph.invoke({"logos": [brand, mark], "products": [red, blue]})

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


def test_try_on_graph_creates_one_image_per_product_model_pair(tmp_path: Path) -> None:
    """两张商品图 × 两张模特图应产出四张换装图，参考图顺序为 [模特, 商品]。"""
    red = write_png(tmp_path / "red.png")
    blue = write_png(tmp_path / "blue.png")
    front = write_png(tmp_path / "front.png")
    side = write_png(tmp_path / "side.png")
    editor = RecordingEditor()

    graph = build_try_on_graph(editor=editor, output_dir=tmp_path / "out")
    result = graph.invoke({"products": [red, blue], "models": [front, side]})

    images = result["try_on_images"]
    assert [(item["product_name"], item["model_name"]) for item in images] == [
        ("red", "front"),
        ("red", "side"),
        ("blue", "front"),
        ("blue", "side"),
    ]
    assert all(Path(item["path"]).is_file() for item in images)
    assert [Path(item["path"]).name for item in images] == [
        "red__front.png",
        "red__side.png",
        "blue__front.png",
        "blue__side.png",
    ]
    assert [call[0] for call in editor.calls] == [
        [front, red],
        [side, red],
        [front, blue],
        [side, blue],
    ]
    assert all(call[1] == TRY_ON_PROMPT for call in editor.calls)
    assert "只替换服装" in TRY_ON_PROMPT
    assert "模特" in TRY_ON_PROMPT
