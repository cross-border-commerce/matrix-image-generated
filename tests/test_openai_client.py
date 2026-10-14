"""读取 .env 中的接口地址和密钥。"""

from product_shoot.openai_client import get_openai_client


def test_get_openai_client_uses_api_key_and_base_url(monkeypatch) -> None:
    """优先使用 OPENAI_API_KEY 与 OPENAI_API_BASE_URL。"""
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_API_BASE_URL", "https://example.com/v1")

    client = get_openai_client()

    assert client.api_key == "sk-test"
    assert str(client.base_url).rstrip("/") == "https://example.com/v1"


def test_get_openai_client_requires_api_key(monkeypatch) -> None:
    """没有密钥时直接报错。"""
    for name in ("API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    try:
        get_openai_client()
    except RuntimeError as exc:
        assert "API_KEY" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
