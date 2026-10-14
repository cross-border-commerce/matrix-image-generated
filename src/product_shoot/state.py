from pathlib import Path
from typing import TypedDict


class ProductPhoto(TypedDict):
    name: str
    photo_path: Path


class ProductImage(TypedDict):
    product_name: str
    logo_name: str
    path: Path


class GraphState(TypedDict, total=False):
    logos: list[Path] | list[ProductPhoto]
    products: list[Path] | list[ProductPhoto]
    placement: str
    product_images: list[ProductImage]


class TryOnImage(TypedDict):
    product_name: str
    model_name: str
    path: Path


class TryOnState(TypedDict, total=False):
    products: list[Path] | list[ProductPhoto]
    models: list[Path] | list[ProductPhoto]
    try_on_images: list[TryOnImage]
