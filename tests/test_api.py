"""HTTP 接口：上传 logo + 实拍，查询任务和下载生成图。"""

from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from tests.image_helpers import MINIMAL_PNG


class RecordingEditor:
    def edit(self, images: list[Path], prompt: str) -> bytes:
        return MINIMAL_PNG


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(data_dir=tmp_path, editor=RecordingEditor()))


def test_create_job_requires_product_photos(tmp_path: Path) -> None:
    """只上传 logo、没有实拍时返回 422。"""
    client = _client(tmp_path)
    response = client.post(
        "/jobs",
        files=[("logo", ("logo.png", MINIMAL_PNG, "image/png"))],
    )
    assert response.status_code == 422


def test_create_job_generates_one_image_per_product(tmp_path: Path) -> None:
    """两张实拍生成两张商品图，可通过 URL 下载。"""
    client = _client(tmp_path)
    response = client.post(
        "/jobs",
        files=[
            ("logo", ("logo.png", MINIMAL_PNG, "image/png")),
            ("products", ("red.png", MINIMAL_PNG, "image/png")),
            ("products", ("blue.png", MINIMAL_PNG, "image/png")),
        ],
        data={"placement": "chest_center"},
    )
    assert response.status_code == 202
    job_id = response.json()["id"]

    job = client.get(f"/jobs/{job_id}")
    assert job.status_code == 200
    body = job.json()
    assert body["status"] == "succeeded"
    assert [item["name"] for item in body["product_images"]] == ["red", "blue"]

    first = client.get(body["product_images"][0]["url"])
    assert first.status_code == 200
    assert first.content == MINIMAL_PNG


def test_get_unknown_job_returns_404(tmp_path: Path) -> None:
    """不存在的任务返回 404。"""
    client = _client(tmp_path)
    response = client.get("/jobs/does-not-exist")
    assert response.status_code == 404


def test_create_try_on_job_requires_product_and_model_photos(tmp_path: Path) -> None:
    """缺少商品图或模特图时返回 422。"""
    client = _client(tmp_path)
    missing_models = client.post(
        "/try-on-jobs",
        files=[("products", ("red.png", MINIMAL_PNG, "image/png"))],
    )
    assert missing_models.status_code == 422
    missing_products = client.post(
        "/try-on-jobs",
        files=[("models", ("front.png", MINIMAL_PNG, "image/png"))],
    )
    assert missing_products.status_code == 422


def test_create_try_on_job_generates_one_image_per_pair(tmp_path: Path) -> None:
    """两张商品图 × 两张模特图生成四张换装图，可通过 URL 下载。"""
    client = _client(tmp_path)
    response = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("red.png", MINIMAL_PNG, "image/png")),
            ("products", ("blue.png", MINIMAL_PNG, "image/png")),
            ("models", ("front.png", MINIMAL_PNG, "image/png")),
            ("models", ("side.png", MINIMAL_PNG, "image/png")),
        ],
    )
    assert response.status_code == 202
    job_id = response.json()["id"]

    job = client.get(f"/try-on-jobs/{job_id}")
    assert job.status_code == 200
    body = job.json()
    assert body["status"] == "succeeded"
    pairs = [(item["product"], item["model"]) for item in body["try_on_images"]]
    assert pairs == [
        ("red", "front"),
        ("red", "side"),
        ("blue", "front"),
        ("blue", "side"),
    ]

    first = client.get(body["try_on_images"][0]["url"])
    assert first.status_code == 200
    assert first.content == MINIMAL_PNG


def test_get_unknown_try_on_job_returns_404(tmp_path: Path) -> None:
    """不存在的换装任务返回 404。"""
    client = _client(tmp_path)
    response = client.get("/try-on-jobs/does-not-exist")
    assert response.status_code == 404
