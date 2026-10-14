from __future__ import annotations

import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api.jobs import Job, JobImage, JobStore
from product_shoot.config import DEFAULT_PLACEMENT
from product_shoot.graph import build_graph
from product_shoot.nodes.image_edit import ImageEditor, OpenAIImageEditor
from product_shoot.nodes.ingest import IngestError
from product_shoot.openai_client import get_openai_client


def create_app(
    data_dir: Path,
    editor: ImageEditor | None = None,
) -> FastAPI:
    data_dir.mkdir(parents=True, exist_ok=True)
    store = JobStore()
    app = FastAPI(title="product-shoot")

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
                    "name": image.name,
                    "url": f"/jobs/{job.id}/files/{image.filename}",
                }
                for image in job.product_images
            ],
            "error": job.error,
        }

    def run_job(job_id: str, placement: str | None) -> None:
        store.update(job_id, status="running")
        root = job_dir(job_id)
        logo = next((root / "logo").iterdir())
        order = (root / "product_order.txt").read_text().splitlines()
        products = [root / "products" / name for name in order if name]
        output_dir = root / "out"
        try:
            graph = build_graph(
                editor=resolve_editor(),
                output_dir=output_dir,
            )
            result = graph.invoke(
                {
                    "logo_path": logo,
                    "products": products,
                    "placement": placement,
                }
            )
            images = [
                JobImage(name=item["name"], filename=Path(item["path"]).name)
                for item in result["product_images"]
            ]
            store.update(
                job_id,
                status="succeeded",
                placement=result["placement"],
                product_images=images,
            )
        except IngestError as exc:
            store.update(job_id, status="failed", error=str(exc))
        except Exception as exc:
            store.update(job_id, status="failed", error=str(exc))

    @app.post("/jobs", status_code=202)
    async def create_job(
        background: BackgroundTasks,
        logo: UploadFile = File(...),
        products: list[UploadFile] = File(...),
        placement: str | None = Form(None),
    ) -> dict:
        if not products:
            raise HTTPException(status_code=422, detail="at least one product photo is required")

        job = store.create()
        root = job_dir(job.id)
        (root / "logo").mkdir(parents=True)
        (root / "products").mkdir(parents=True)

        logo_path = root / "logo" / (logo.filename or "logo.png")
        logo_path.write_bytes(await logo.read())
        product_names: list[str] = []
        for index, product in enumerate(products):
            dest = root / "products" / (product.filename or f"product-{index}.png")
            dest.write_bytes(await product.read())
            product_names.append(dest.name)
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

    return app


def create_default_app() -> FastAPI:
    return create_app(Path(os.environ.get("DATA_DIR", "data")))
