from pathlib import Path
from typing import TypedDict


class ProductPhoto(TypedDict):
    name: str
    photo_path: Path


class ProductImage(TypedDict):
    name: str
    path: Path


class GraphState(TypedDict, total=False):
    logo_path: Path
    products: list[Path] | list[ProductPhoto]
    placement: str
    product_images: list[ProductImage]
