from collections.abc import Callable
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from product_shoot.nodes.image_edit import ImageEditor
from product_shoot.nodes.prompts import (
    TRY_ON_PROMPT,
    TRY_ON_PROMPT_WITH_PRINT,
    render_image_prompt,
)
from product_shoot.state import GraphState, TryOnState


def build_graph(
    editor: ImageEditor,
    output_dir: Path,
    render_prompt: Callable[[str], str] = render_image_prompt,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    def generate_node(state: GraphState) -> GraphState:
        prompt = render_prompt(state["placement"])
        images = []
        for item in state["work_items"]:
            image_bytes = editor.edit(
                [item["product_path"], item["logo_path"]],
                prompt,
            )
            dest = output_dir / f"{item['product_name']}__{item['logo_name']}.png"
            dest.write_bytes(image_bytes)
            images.append(
                {
                    "product_name": item["product_name"],
                    "logo_name": item["logo_name"],
                    "path": dest,
                }
            )
        return {"product_images": images}

    builder = StateGraph(GraphState)
    builder.add_node("generate", generate_node)
    builder.add_edge(START, "generate")
    builder.add_edge("generate", END)
    return builder.compile()


def build_try_on_graph(
    editor: ImageEditor,
    output_dir: Path,
    on_image: Callable[[dict[str, Any]], None] | None = None,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    def try_on_node(state: TryOnState) -> TryOnState:
        images = []
        for item in state["work_items"]:
            references = [item["model_path"], *item["product_paths"]]
            prompt = TRY_ON_PROMPT
            logo_path = item.get("logo_path")
            logo_name = item.get("logo_name")
            if logo_path:
                references.append(logo_path)
                prompt = TRY_ON_PROMPT_WITH_PRINT
            if logo_name:
                filename = f"{item['product_name']}__{item['model_name']}__{logo_name}.png"
            else:
                filename = f"{item['product_name']}__{item['model_name']}.png"
            image_bytes = editor.edit(references, prompt)
            dest = output_dir / filename
            dest.write_bytes(image_bytes)
            generated = {
                "product_name": item["product_name"],
                "model_name": item["model_name"],
                "logo_name": logo_name,
                "path": dest,
            }
            images.append(generated)
            if on_image is not None:
                on_image(generated)
        return {"try_on_images": images}

    builder = StateGraph(TryOnState)
    builder.add_node("try_on", try_on_node)
    builder.add_edge(START, "try_on")
    builder.add_edge("try_on", END)
    return builder.compile()
