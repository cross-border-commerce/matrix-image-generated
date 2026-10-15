from __future__ import annotations

import re
from pathlib import Path

from product_shoot.state import ProductPhoto

VIEW_TOKENS = (
    "正面",
    "背面",
    "侧面",
    "细节",
    "局部",
    "front",
    "back",
    "side",
    "detail",
)
_VIEW_SET = {token.lower() for token in VIEW_TOKENS}
_SPLIT = re.compile(r"[-_\s]+")


def canonical_product_id(filename: str) -> str:
    stem = Path(filename).stem
    parts = [part for part in _SPLIT.split(stem) if part]
    kept = [part for part in parts if part.lower() not in _VIEW_SET]
    if kept:
        return "-".join(kept)
    return ""


def _logical_parent(name: str) -> str | None:
    parent = Path(name).parent
    if parent == Path("."):
        return None
    return str(parent)


def group_products(products: list[ProductPhoto]) -> list[dict]:
    n = len(products)
    parent_of = list(range(n))

    def find(i: int) -> int:
        while parent_of[i] != i:
            parent_of[i] = parent_of[parent_of[i]]
            i = parent_of[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent_of[rj] = ri

    stems = [canonical_product_id(item["name"]) for item in products]
    parents = [_logical_parent(item["name"]) for item in products]

    stem_index: dict[str, int] = {}
    for i, stem in enumerate(stems):
        if stem:
            if stem in stem_index:
                union(stem_index[stem], i)
            else:
                stem_index[stem] = i

    dir_files: dict[str, list[int]] = {}
    for i, parent in enumerate(parents):
        if parent is not None:
            dir_files.setdefault(parent, []).append(i)
    for indexes in dir_files.values():
        unique_stems = {stems[i] for i in indexes if stems[i]}
        if len(unique_stems) <= 1:
            for other in indexes[1:]:
                union(indexes[0], other)

    buckets: dict[int, list[int]] = {}
    for i in range(n):
        buckets.setdefault(find(i), []).append(i)

    groups = []
    for root, indexes in buckets.items():
        first = products[indexes[0]]
        stem = stems[indexes[0]]
        parent = parents[indexes[0]]
        group_id = stem or parent or Path(first["name"]).stem
        groups.append(
            {
                "id": group_id,
                "photos": [products[i] for i in indexes],
            }
        )
    return groups


def pair_models(
    models: list[ProductPhoto],
    groups: list[dict],
    assignments: dict[str, str] | None = None,
) -> list[tuple[ProductPhoto, dict]]:
    if not models or not groups:
        return []

    by_id = {group["id"]: group for group in groups}
    pairs = []
    for i, model in enumerate(models):
        group = groups[i % len(groups)]
        if assignments:
            assigned = assignments.get(model["name"])
            if assigned in by_id:
                group = by_id[assigned]
        pairs.append((model, group))
    return pairs


def expand_generate_work_items(
    groups: list[dict],
    logos: list[ProductPhoto],
) -> list[dict]:
    items = []
    for group in groups:
        product_path = group["photos"][0]["photo_path"]
        for logo in logos:
            items.append(
                {
                    "product_name": group["id"],
                    "logo_name": logo["name"],
                    "product_path": product_path,
                    "logo_path": logo["photo_path"],
                }
            )
    return items


def _assignments_for_logo(
    assignments: dict | None,
    logo_name: str,
) -> dict[str, str] | None:
    if not assignments:
        return None
    nested = assignments.get(logo_name)
    if isinstance(nested, dict):
        return {str(key): str(value) for key, value in nested.items()}
    if all(not isinstance(value, dict) for value in assignments.values()):
        return {str(key): str(value) for key, value in assignments.items()}
    return None


def expand_try_on_work_items(
    logos: list[ProductPhoto],
    models: list[ProductPhoto],
    groups: list[dict],
    assignments: dict | None = None,
) -> list[dict]:
    items = []
    for logo in logos:
        pairs = pair_models(
            models,
            groups,
            assignments=_assignments_for_logo(assignments, logo["name"]),
        )
        for model, group in pairs:
            items.append(
                {
                    "product_name": group["id"],
                    "model_name": model["name"],
                    "product_paths": [photo["photo_path"] for photo in group["photos"]],
                    "model_path": model["photo_path"],
                    "logo_name": logo["name"],
                    "logo_path": logo["photo_path"],
                }
            )
    return items
