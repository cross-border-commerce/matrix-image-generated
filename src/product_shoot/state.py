from pathlib import Path
from typing import TypedDict


class ProductPhoto(TypedDict):
    name: str
    photo_path: Path


class ProductImage(TypedDict):
    product_name: str
    logo_name: str
    path: Path


class GenerateWorkItem(TypedDict):
    product_name: str
    logo_name: str
    product_path: Path
    logo_path: Path


class GraphState(TypedDict, total=False):
    placement: str
    work_items: list[GenerateWorkItem]
    product_images: list[ProductImage]


class TryOnImage(TypedDict, total=False):
    product_name: str
    model_name: str
    logo_name: str | None
    path: Path


class TryOnWorkItem(TypedDict, total=False):
    product_name: str
    model_name: str
    product_paths: list[Path]
    model_path: Path
    logo_name: str | None
    logo_path: Path | None


class TryOnState(TypedDict, total=False):
    work_items: list[TryOnWorkItem]
    try_on_images: list[TryOnImage]
