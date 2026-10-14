"""pytest 公共夹具。"""

import os

import pytest


@pytest.fixture(autouse=True)
def _drop_unsupported_socks_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """本机若设置了 socks:// 代理，httpx 会报错，测试里去掉。"""
    for name in (
        "ALL_PROXY",
        "all_proxy",
        "HTTP_PROXY",
        "http_proxy",
        "HTTPS_PROXY",
        "https_proxy",
    ):
        current = os.environ.get(name, "")
        if current.startswith("socks://"):
            monkeypatch.delenv(name, raising=False)
