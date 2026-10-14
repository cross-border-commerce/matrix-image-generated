from collections.abc import Callable
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from product_shoot.nodes.image_edit import ImageEditor
from product_shoot.nodes.ingest import ingest
from product_shoot.nodes.prompts import render_image_prompt
from product_shoot.state import GraphState, ProductPhoto


def build_graph(
    editor: ImageEditor,
    output_dir: Path,
    render_prompt: Callable[[str], str] = render_image_prompt,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    def ingest_node(state: GraphState) -> GraphState:
        raw_products = state["products"]
        if raw_products and isinstance(raw_products[0], dict):
            paths = [item["photo_path"] for item in raw_products]
        else:
            paths = list(raw_products)
        return ingest(
            logo=state["logo_path"],
            products=paths,
            placement=state.get("placement"),
        )

    def generate_node(state: GraphState) -> GraphState:
        prompt = render_prompt(state["placement"])
        images = []
        for item in state["products"]:
            photo: ProductPhoto = item  # type: ignore[assignment]
            image_bytes = editor.edit(
                [photo["photo_path"], state["logo_path"]],
                prompt,
            )
            dest = output_dir / f"{photo['name']}.png"
            dest.write_bytes(image_bytes)
            images.append({"name": photo["name"], "path": dest})
        return {"product_images": images}

    builder = StateGraph(GraphState)
    builder.add_node("ingest", ingest_node)
    builder.add_node("generate", generate_node)
    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "generate")
    builder.add_edge("generate", END)
    return builder.compile()
