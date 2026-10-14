from collections.abc import Callable
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from product_shoot.nodes.image_edit import ImageEditor
from product_shoot.nodes.ingest import ingest, ingest_try_on
from product_shoot.nodes.prompts import TRY_ON_PROMPT, render_image_prompt
from product_shoot.state import GraphState, ProductPhoto, TryOnState


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


def build_try_on_graph(editor: ImageEditor, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    def ingest_node(state: TryOnState) -> TryOnState:
        raw_products = state["products"]
        raw_models = state["models"]
        products = (
            [item["photo_path"] for item in raw_products]
            if raw_products and isinstance(raw_products[0], dict)
            else list(raw_products)
        )
        models = (
            [item["photo_path"] for item in raw_models]
            if raw_models and isinstance(raw_models[0], dict)
            else list(raw_models)
        )
        return ingest_try_on(products=products, models=models)

    def try_on_node(state: TryOnState) -> TryOnState:
        images = []
        for product in state["products"]:
            product_photo: ProductPhoto = product  # type: ignore[assignment]
            for model in state["models"]:
                model_photo: ProductPhoto = model  # type: ignore[assignment]
                image_bytes = editor.edit(
                    [model_photo["photo_path"], product_photo["photo_path"]],
                    TRY_ON_PROMPT,
                )
                dest = output_dir / f"{product_photo['name']}__{model_photo['name']}.png"
                dest.write_bytes(image_bytes)
                images.append(
                    {
                        "product_name": product_photo["name"],
                        "model_name": model_photo["name"],
                        "path": dest,
                    }
                )
        return {"try_on_images": images}

    builder = StateGraph(TryOnState)
    builder.add_node("ingest", ingest_node)
    builder.add_node("try_on", try_on_node)
    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "try_on")
    builder.add_edge("try_on", END)
    return builder.compile()
