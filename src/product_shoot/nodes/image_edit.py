import base64
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

import httpx

from product_shoot.config import IMAGE_MODEL


class ImageEditor(Protocol):
    def edit(self, images: Sequence[Path], prompt: str) -> bytes: ...


def download_image(url: str) -> bytes:
    """网关只给图片 URL 时，把文件拉下来。不走本机代理，避免 socks/https 代理握手失败。"""
    with httpx.Client(trust_env=False, timeout=60.0) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


class OpenAIImageEditor:
    def __init__(
        self,
        client,
        model: str = IMAGE_MODEL,
        download: Callable[[str], bytes] = download_image,
    ) -> None:
        self.client = client
        self.model = model
        self.download = download

    def edit(self, images: Sequence[Path], prompt: str) -> bytes:
        handles = [path.open("rb") for path in images]
        try:
            result = self.client.images.edit(
                model=self.model,
                image=handles,
                prompt=prompt,
            )
        finally:
            for handle in handles:
                handle.close()

        item = result.data[0]
        encoded = item.b64_json
        if encoded:
            return base64.b64decode(encoded)
        url = getattr(item, "url", None)
        if url:
            return self.download(url)
        raise RuntimeError("image edit returned no image data")
