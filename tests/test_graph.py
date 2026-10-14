"""工作流：每种颜色的实拍各生成一张商品图（编辑器用假实现）。"""

from pathlib import Path

from product_shoot.graph import build_graph
from tests.image_helpers import MINIMAL_PNG, write_png


class RecordingEditor:
    """记下每次生图调用的参考图和提示词。"""

    def __init__(self) -> None:
        self.calls: list[tuple[list[Path], str]] = []

    def edit(self, images: list[Path], prompt: str) -> bytes:
        self.calls.append((list(images), prompt))
        return MINIMAL_PNG


def test_graph_creates_one_product_image_per_photo(tmp_path: Path) -> None:
    """两张实拍应产出两张图，参考图顺序为 [实拍, logo]，提示词已填入胸前。"""
    logo = write_png(tmp_path / "logo.png")
    red = write_png(tmp_path / "red.png")
    blue = write_png(tmp_path / "blue.png")
    editor = RecordingEditor()

    graph = build_graph(editor=editor, output_dir=tmp_path / "out")
    result = graph.invoke({"logo_path": logo, "products": [red, blue]})

    images = result["product_images"]
    assert [item["name"] for item in images] == ["red", "blue"]
    assert all(Path(item["path"]).is_file() for item in images)
    assert [call[0] for call in editor.calls] == [[red, logo], [blue, logo]]
    assert all("胸前" in call[1] for call in editor.calls)
    assert all("{placement}" not in call[1] for call in editor.calls)
