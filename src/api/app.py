from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.jobs import Job, JobImage, JobStore, TryOnJobImage
from product_shoot.config import DEFAULT_PLACEMENT
from product_shoot.graph import build_graph, build_try_on_graph
from product_shoot.nodes.image_edit import ImageEditor, OpenAIImageEditor
from product_shoot.nodes.ingest import IngestError, ingest, ingest_try_on
from product_shoot.openai_client import get_openai_client
from product_shoot.pairing import (
    expand_generate_work_items,
    expand_try_on_work_items,
    group_products,
)


def _relative_filename(filename: str | None, fallback: str) -> str:
    rel = Path(filename or fallback)
    if rel.is_absolute() or ".." in rel.parts:
        rel = Path(rel.name)
    return rel.as_posix()


async def _save_uploads(
    dest_dir: Path,
    uploads: list[UploadFile],
    prefix: str,
) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for index, upload in enumerate(uploads):
        rel = _relative_filename(upload.filename, f"{prefix}-{index}.png")
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(await upload.read())
        names.append(rel)
    return names


def _photos(root: Path, folder: str, names: list[str], *, use_stem: bool) -> list[dict]:
    photos = []
    for name in names:
        if not name:
            continue
        photos.append(
            {
                "name": Path(name).stem if use_stem else name,
                "photo_path": root / folder / name,
            }
        )
    return photos


def _parse_assignments(raw: str | None) -> dict[str, str] | None:
    if raw is None or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail="apparelColorAssignments must be a JSON object",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=422,
            detail="apparelColorAssignments must be a JSON object",
        )
    parsed: dict = {}
    for key, value in data.items():
        if isinstance(value, dict):
            parsed[str(key)] = {str(inner_key): str(inner_value) for inner_key, inner_value in value.items()}
        else:
            parsed[str(key)] = str(value)
    return parsed


def create_app(
    data_dir: Path,
    editor: ImageEditor | None = None,
) -> FastAPI:
    data_dir.mkdir(parents=True, exist_ok=True)
    store = JobStore()
    try_on_store = JobStore()
    app = FastAPI(title="product-shoot")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def resolve_editor() -> ImageEditor:
        if editor is not None:
            return editor
        return OpenAIImageEditor(get_openai_client())

    def job_dir(job_id: str) -> Path:
        return data_dir / "jobs" / job_id

    def serialize(job: Job) -> dict:
        return {
            "id": job.id,
            "status": job.status,
            "placement": job.placement,
            "product_images": [
                {
                    "product": image.product,
                    "logo": image.logo,
                    "url": f"/jobs/{job.id}/files/{image.filename}",
                }
                for image in job.product_images
            ],
            "error": job.error,
        }

    def run_job(job_id: str, placement: str | None) -> None:
        store.update(job_id, status="running")
        root = job_dir(job_id)
        logo_order = (root / "logo_order.txt").read_text().splitlines()
        product_order = (root / "product_order.txt").read_text().splitlines()
        logo_paths = [root / "logos" / name for name in logo_order if name]
        product_paths = [root / "products" / name for name in product_order if name]
        output_dir = root / "out"
        try:
            validated = ingest(
                logos=logo_paths,
                products=product_paths,
                placement=placement,
            )
            groups = group_products(
                _photos(root, "products", product_order, use_stem=False)
            )
            work_items = expand_generate_work_items(groups, validated["logos"])
            graph = build_graph(
                editor=resolve_editor(),
                output_dir=output_dir,
            )
            result = graph.invoke(
                {
                    "placement": validated["placement"],
                    "work_items": work_items,
                }
            )
            images = [
                JobImage(
                    product=item["product_name"],
                    logo=item["logo_name"],
                    filename=Path(item["path"]).name,
                )
                for item in result["product_images"]
            ]
            store.update(
                job_id,
                status="succeeded",
                placement=validated["placement"],
                product_images=images,
            )
        except IngestError as exc:
            store.update(job_id, status="failed", error=str(exc))
        except Exception as exc:
            store.update(job_id, status="failed", error=str(exc))

    @app.post("/jobs", status_code=202)
    async def create_job(
        background: BackgroundTasks,
        logos: list[UploadFile] = File(...),
        products: list[UploadFile] = File(...),
        placement: str | None = Form(None),
    ) -> dict:
        if not logos:
            raise HTTPException(status_code=422, detail="at least one logo photo is required")
        if not products:
            raise HTTPException(status_code=422, detail="at least one product photo is required")

        job = store.create()
        root = job_dir(job.id)
        logo_names = await _save_uploads(root / "logos", logos, "logo")
        product_names = await _save_uploads(root / "products", products, "product")
        (root / "logo_order.txt").write_text("\n".join(logo_names))
        (root / "product_order.txt").write_text("\n".join(product_names))

        background.add_task(run_job, job.id, placement or DEFAULT_PLACEMENT)
        return serialize(job)

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return serialize(job)

    @app.get("/jobs/{job_id}/files/{filename}")
    def get_job_file(job_id: str, filename: str):
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        if Path(filename).name != filename:
            raise HTTPException(status_code=400, detail="invalid filename")
        path = job_dir(job_id) / "out" / filename
        if not path.is_file():
            raise HTTPException(status_code=404, detail="file not found")
        return FileResponse(path)

    def try_on_job_dir(job_id: str) -> Path:
        return data_dir / "try-on-jobs" / job_id

    def serialize_try_on(job: Job) -> dict:
        images = []
        for image in job.try_on_images:
            item = {
                "product": image.product,
                "model": image.model,
                "url": f"/try-on-jobs/{job.id}/files/{image.filename}",
            }
            if image.logo:
                item["logo"] = image.logo
            images.append(item)
        return {
            "id": job.id,
            "status": job.status,
            "try_on_images": images,
            "error": job.error,
        }

    def run_try_on_job(job_id: str) -> None:
        try_on_store.update(job_id, status="running")
        root = try_on_job_dir(job_id)
        product_order = (root / "product_order.txt").read_text().splitlines()
        model_order = (root / "model_order.txt").read_text().splitlines()
        logo_order_path = root / "logo_order.txt"
        logo_order = (
            logo_order_path.read_text().splitlines() if logo_order_path.is_file() else []
        )
        assignments_path = root / "assignments.json"
        assignments = (
            json.loads(assignments_path.read_text()) if assignments_path.is_file() else None
        )
        product_paths = [root / "products" / name for name in product_order if name]
        model_paths = [root / "models" / name for name in model_order if name]
        logo_paths = [root / "logos" / name for name in logo_order if name]
        output_dir = root / "out"
        try:
            ingest_try_on(products=product_paths, models=model_paths)
            if not logo_paths:
                raise IngestError("at least one logo photo is required")
            logos = ingest(logos=logo_paths, products=product_paths)["logos"]
            groups = group_products(
                _photos(root, "products", product_order, use_stem=False)
            )
            models = _photos(root, "models", model_order, use_stem=True)
            work_items = expand_try_on_work_items(
                logos,
                models,
                groups,
                assignments=assignments,
            )
            def on_image(item: dict) -> None:
                job = try_on_store.get(job_id)
                current = list(job.try_on_images) if job else []
                current.append(
                    TryOnJobImage(
                        product=item["product_name"],
                        model=item["model_name"],
                        filename=Path(item["path"]).name,
                        logo=item.get("logo_name"),
                    )
                )
                try_on_store.update(job_id, try_on_images=current)

            graph = build_try_on_graph(
                editor=resolve_editor(),
                output_dir=output_dir,
                on_image=on_image,
            )
            result = graph.invoke({"work_items": work_items})
            images = [
                TryOnJobImage(
                    product=item["product_name"],
                    model=item["model_name"],
                    filename=Path(item["path"]).name,
                    logo=item.get("logo_name"),
                )
                for item in result["try_on_images"]
            ]
            try_on_store.update(job_id, status="succeeded", try_on_images=images)
        except IngestError as exc:
            try_on_store.update(job_id, status="failed", error=str(exc))
        except Exception as exc:
            try_on_store.update(job_id, status="failed", error=str(exc))

    @app.post("/try-on-jobs", status_code=202)
    async def create_try_on_job(
        background: BackgroundTasks,
        products: list[UploadFile] = File(...),
        models: list[UploadFile] = File(...),
        logos: list[UploadFile] = File(...),
        apparelColorAssignments: str | None = Form(None),
    ) -> dict:
        if not products:
            raise HTTPException(status_code=422, detail="at least one product photo is required")
        if not models:
            raise HTTPException(status_code=422, detail="at least one model photo is required")
        if not logos:
            raise HTTPException(status_code=422, detail="at least one logo photo is required")

        assignments = _parse_assignments(apparelColorAssignments)
        job = try_on_store.create()
        root = try_on_job_dir(job.id)
        product_names = await _save_uploads(root / "products", products, "product")
        model_names = await _save_uploads(root / "models", models, "model")
        (root / "product_order.txt").write_text("\n".join(product_names))
        (root / "model_order.txt").write_text("\n".join(model_names))
        logo_names = await _save_uploads(root / "logos", logos, "logo")
        (root / "logo_order.txt").write_text("\n".join(logo_names))
        if assignments:
            (root / "assignments.json").write_text(
                json.dumps(assignments, ensure_ascii=False)
            )

        background.add_task(run_try_on_job, job.id)
        return serialize_try_on(job)

    @app.get("/try-on-jobs/{job_id}")
    def get_try_on_job(job_id: str) -> dict:
        job = try_on_store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return serialize_try_on(job)

    @app.get("/try-on-jobs/{job_id}/files/{filename}")
    def get_try_on_job_file(job_id: str, filename: str):
        job = try_on_store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        if Path(filename).name != filename:
            raise HTTPException(status_code=400, detail="invalid filename")
        path = try_on_job_dir(job_id) / "out" / filename
        if not path.is_file():
            raise HTTPException(status_code=404, detail="file not found")
        return FileResponse(path)

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


def create_default_app() -> FastAPI:
    return create_app(Path(os.environ.get("DATA_DIR", "data")))
