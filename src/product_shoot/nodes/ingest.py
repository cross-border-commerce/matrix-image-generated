from pathlib import Path

from product_shoot.config import ALLOWED_IMAGE_SUFFIXES, DEFAULT_PLACEMENT


class IngestError(ValueError):
    pass


def _require_image(path: Path, label: str) -> None:
    if path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
        raise IngestError(f"unsupported {label} type: {path.suffix}")
    if not path.is_file():
        raise IngestError(f"{label} file not found: {path}")


def ingest(
    logo: Path,
    products: list[Path],
    placement: str | None = None,
) -> dict:
    if not products:
        raise IngestError("at least one product photo is required")

    _require_image(logo, "logo")
    for product in products:
        _require_image(product, "product")

    return {
        "logo_path": logo,
        "placement": placement or DEFAULT_PLACEMENT,
        "products": [
            {"name": product.stem, "photo_path": product} for product in products
        ],
    }
