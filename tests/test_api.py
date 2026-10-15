"""HTTP 接口：分组配对在接口完成，图节点只消费工作项。"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from tests.image_helpers import MINIMAL_PNG


class RecordingEditor:
    def __init__(self) -> None:
        self.calls: list[tuple[list[Path], str]] = []

    def edit(self, images: list[Path], prompt: str) -> bytes:
        self.calls.append((list(images), prompt))
        return MINIMAL_PNG


def _client(tmp_path: Path, editor: RecordingEditor | None = None) -> TestClient:
    return TestClient(create_app(data_dir=tmp_path, editor=editor or RecordingEditor()))


def test_create_job_requires_logo_and_product_photos(tmp_path: Path) -> None:
    """缺少印花或实拍时返回 422。"""
    client = _client(tmp_path)
    missing_products = client.post(
        "/jobs",
        files=[("logos", ("brand.png", MINIMAL_PNG, "image/png"))],
    )
    assert missing_products.status_code == 422
    missing_logos = client.post(
        "/jobs",
        files=[("products", ("red.png", MINIMAL_PNG, "image/png"))],
    )
    assert missing_logos.status_code == 422


def test_create_job_generates_one_image_per_pair(tmp_path: Path) -> None:
    """两件商品 × 两张印花生成四张商品图，可通过 URL 下载。"""
    client = _client(tmp_path)
    response = client.post(
        "/jobs",
        files=[
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
            ("logos", ("mark.png", MINIMAL_PNG, "image/png")),
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
    pairs = [(item["product"], item["logo"]) for item in body["product_images"]]
    assert pairs == [
        ("red", "brand"),
        ("red", "mark"),
        ("blue", "brand"),
        ("blue", "mark"),
    ]

    first = client.get(body["product_images"][0]["url"])
    assert first.status_code == 200
    assert first.content == MINIMAL_PNG


def test_create_job_groups_product_views_before_crossing_logos(tmp_path: Path) -> None:
    """同一件商品的多角度实拍先收成一件，再和每张印花配成工作项。"""
    editor = RecordingEditor()
    client = _client(tmp_path, editor)
    response = client.post(
        "/jobs",
        files=[
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
            ("logos", ("mark.png", MINIMAL_PNG, "image/png")),
            ("products", ("白色-正面.jpeg", MINIMAL_PNG, "image/jpeg")),
            ("products", ("白色-背面.jpeg", MINIMAL_PNG, "image/jpeg")),
        ],
    )
    assert response.status_code == 202
    body = client.get(f"/jobs/{response.json()['id']}").json()
    pairs = [(item["product"], item["logo"]) for item in body["product_images"]]
    assert pairs == [("白色", "brand"), ("白色", "mark")]
    assert len(editor.calls) == 2
    assert Path(editor.calls[0][0][0]).name == "白色-正面.jpeg"
    assert Path(editor.calls[0][0][1]).name == "brand.png"


def test_get_unknown_job_returns_404(tmp_path: Path) -> None:
    """不存在的任务返回 404。"""
    client = _client(tmp_path)
    response = client.get("/jobs/does-not-exist")
    assert response.status_code == 404


def test_create_try_on_job_requires_product_model_and_logo_photos(tmp_path: Path) -> None:
    """缺少商品图、模特图或印花时返回 422。"""
    client = _client(tmp_path)
    missing_models = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("red.png", MINIMAL_PNG, "image/png")),
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
        ],
    )
    assert missing_models.status_code == 422
    missing_products = client.post(
        "/try-on-jobs",
        files=[
            ("models", ("front.png", MINIMAL_PNG, "image/png")),
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
        ],
    )
    assert missing_products.status_code == 422
    missing_logos = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("red.png", MINIMAL_PNG, "image/png")),
            ("models", ("front.png", MINIMAL_PNG, "image/png")),
        ],
    )
    assert missing_logos.status_code == 422


def test_create_try_on_job_pairs_each_model_with_one_product(tmp_path: Path) -> None:
    """没有子目录的模特图算一组；一个 logo 配这一组，组内每张参考图配一件商品。"""
    client = _client(tmp_path)
    response = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("red.png", MINIMAL_PNG, "image/png")),
            ("products", ("blue.png", MINIMAL_PNG, "image/png")),
            ("models", ("front.png", MINIMAL_PNG, "image/png")),
            ("models", ("side.png", MINIMAL_PNG, "image/png")),
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
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
        ("blue", "side"),
    ]
    assert [item.get("logo") for item in body["try_on_images"]] == ["brand", "brand"]

    first = client.get(body["try_on_images"][0]["url"])
    assert first.status_code == 200
    assert first.content == MINIMAL_PNG


def test_create_try_on_job_groups_model_subdirectories_and_cycles(tmp_path: Path) -> None:
    """每个子目录是一组模特；一个 logo 配一组，组内每张参考图配不同商品。"""
    client = _client(tmp_path)
    response = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("A.png", MINIMAL_PNG, "image/png")),
            ("products", ("B.png", MINIMAL_PNG, "image/png")),
            ("products", ("C.png", MINIMAL_PNG, "image/png")),
            ("models", ("model1/a1.jpg", MINIMAL_PNG, "image/jpeg")),
            ("models", ("model1/a2.jpg", MINIMAL_PNG, "image/jpeg")),
            ("models", ("model2/b1.jpg", MINIMAL_PNG, "image/jpeg")),
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
            ("logos", ("mark.png", MINIMAL_PNG, "image/png")),
        ],
    )
    body = client.get(f"/try-on-jobs/{response.json()['id']}").json()
    assert [(item["product"], item["model"], item.get("logo")) for item in body["try_on_images"]] == [
        ("A", "a1", "brand"),
        ("B", "a2", "brand"),
        ("A", "b1", "mark"),
    ]


def test_create_try_on_job_groups_same_upload_directory(tmp_path: Path) -> None:
    """上传文件名带同一子目录时，目录内多张图算同一件。"""
    editor = RecordingEditor()
    client = _client(tmp_path, editor)
    response = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("white/front.jpeg", MINIMAL_PNG, "image/jpeg")),
            ("products", ("white/back.jpeg", MINIMAL_PNG, "image/jpeg")),
            ("models", ("m1.png", MINIMAL_PNG, "image/png")),
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
        ],
    )
    body = client.get(f"/try-on-jobs/{response.json()['id']}").json()
    assert [(item["product"], item["model"]) for item in body["try_on_images"]] == [
        ("white", "m1")
    ]
    assert [path.name for path in editor.calls[0][0]] == [
        "m1.png",
        "front.jpeg",
        "back.jpeg",
        "brand.png",
    ]


def test_create_try_on_job_sends_grouped_views_together(tmp_path: Path) -> None:
    """同一件的多角度商品图在同一次换装 edit 里当参考。"""
    editor = RecordingEditor()
    client = _client(tmp_path, editor)
    response = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("白色-正面.jpeg", MINIMAL_PNG, "image/jpeg")),
            ("products", ("白色-背面.jpeg", MINIMAL_PNG, "image/jpeg")),
            ("models", ("m1.png", MINIMAL_PNG, "image/png")),
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
        ],
    )
    assert response.status_code == 202
    body = client.get(f"/try-on-jobs/{response.json()['id']}").json()
    assert [(item["product"], item["model"]) for item in body["try_on_images"]] == [
        ("白色", "m1")
    ]
    assert len(editor.calls) == 1
    assert [path.name for path in editor.calls[0][0]] == [
        "m1.png",
        "白色-正面.jpeg",
        "白色-背面.jpeg",
        "brand.png",
    ]


def test_create_try_on_job_is_logo_by_reference_and_honors_assignments(
    tmp_path: Path,
) -> None:
    """组内行号指定覆盖默认商品配对。"""
    client = _client(tmp_path)
    response = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("white.png", MINIMAL_PNG, "image/png")),
            ("products", ("black.png", MINIMAL_PNG, "image/png")),
            ("products", ("navy.png", MINIMAL_PNG, "image/png")),
            ("models", ("model1/m1.png", MINIMAL_PNG, "image/png")),
            ("models", ("model1/m1b.png", MINIMAL_PNG, "image/png")),
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
        ],
        data={"apparelColorAssignments": json.dumps({"0": "navy"})},
    )
    body = client.get(f"/try-on-jobs/{response.json()['id']}").json()
    assert [(item["product"], item["model"], item.get("logo")) for item in body["try_on_images"]] == [
        ("navy", "m1", "brand"),
        ("black", "m1b", "brand"),
    ]


def test_create_try_on_job_assignments_can_differ_per_logo(tmp_path: Path) -> None:
    """同一行在不同印花下可以配不同商品。"""
    client = _client(tmp_path)
    response = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("white.png", MINIMAL_PNG, "image/png")),
            ("products", ("black.png", MINIMAL_PNG, "image/png")),
            ("models", ("model1/m1.png", MINIMAL_PNG, "image/png")),
            ("models", ("model2/m2.png", MINIMAL_PNG, "image/png")),
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
            ("logos", ("mark.png", MINIMAL_PNG, "image/png")),
        ],
        data={
            "apparelColorAssignments": json.dumps(
                {"brand": {"0": "black"}, "mark": {"0": "white"}}
            )
        },
    )
    body = client.get(f"/try-on-jobs/{response.json()['id']}").json()
    assert [
        (item["product"], item["model"], item.get("logo"))
        for item in body["try_on_images"]
    ] == [
        ("black", "m1", "brand"),
        ("white", "m2", "mark"),
    ]


def test_create_try_on_job_uses_assignments_when_models_cover_products(
    tmp_path: Path,
) -> None:
    """组内参考图可用 apparelColorAssignments 指定某一张配哪件。"""
    client = _client(tmp_path)
    response = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("white.png", MINIMAL_PNG, "image/png")),
            ("products", ("black.png", MINIMAL_PNG, "image/png")),
            ("models", ("model1/m1.png", MINIMAL_PNG, "image/png")),
            ("models", ("model1/m2.png", MINIMAL_PNG, "image/png")),
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
        ],
        data={"apparelColorAssignments": json.dumps({"0": "black", "1": "white"})},
    )
    body = client.get(f"/try-on-jobs/{response.json()['id']}").json()
    assert [(item["product"], item["model"]) for item in body["try_on_images"]] == [
        ("black", "m1"),
        ("white", "m2"),
    ]


def test_create_try_on_job_multiplies_pairs_by_prints(tmp_path: Path) -> None:
    """每个 logo 配一组参考图，组内每张出一张，logo 作为最后一张参考图。"""
    editor = RecordingEditor()
    client = _client(tmp_path, editor)
    response = client.post(
        "/try-on-jobs",
        files=[
            ("products", ("white.png", MINIMAL_PNG, "image/png")),
            ("products", ("black.png", MINIMAL_PNG, "image/png")),
            ("models", ("model1/m1.png", MINIMAL_PNG, "image/png")),
            ("models", ("model2/m2.png", MINIMAL_PNG, "image/png")),
            ("logos", ("brand.png", MINIMAL_PNG, "image/png")),
            ("logos", ("mark.png", MINIMAL_PNG, "image/png")),
        ],
    )
    body = client.get(f"/try-on-jobs/{response.json()['id']}").json()
    triples = [
        (item["product"], item["model"], item.get("logo"))
        for item in body["try_on_images"]
    ]
    assert triples == [
        ("white", "m1", "brand"),
        ("white", "m2", "mark"),
    ]
    assert [path.name for path in editor.calls[0][0]] == [
        "m1.png",
        "white.png",
        "brand.png",
    ]


def test_get_unknown_try_on_job_returns_404(tmp_path: Path) -> None:
    """不存在的换装任务返回 404。"""
    client = _client(tmp_path)
    response = client.get("/try-on-jobs/does-not-exist")
    assert response.status_code == 404
