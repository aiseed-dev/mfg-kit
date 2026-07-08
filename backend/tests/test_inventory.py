import httpx
import pytest

from app.core.config import settings
from app.services import inventory


async def test_fetch_returns_none_when_kikan_url_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "kikan_url", "")
    assert await inventory.fetch() is None


async def test_fetch_returns_data_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "kikan_url", "http://kikan.example.jp")

    async def fake_get(
        self: httpx.AsyncClient, url: str, **kw: object
    ) -> httpx.Response:
        assert url == "http://kikan.example.jp/inventory"
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json=[
                {"code": "DR-100", "qty": 5, "price": 300000},
                {"code": "MC-300", "qty": 0},
            ],
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = await inventory.fetch()
    assert result == {
        "DR-100": {"code": "DR-100", "qty": 5, "price": 300000},
        "MC-300": {"code": "MC-300", "qty": 0},
    }


async def test_fetch_returns_none_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "kikan_url", "http://kikan.example.jp")

    async def fake_get(
        self: httpx.AsyncClient, url: str, **kw: object
    ) -> httpx.Response:
        raise httpx.ConnectError("接続できません", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    assert await inventory.fetch() is None


async def test_fetch_returns_none_on_http_error_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "kikan_url", "http://kikan.example.jp")

    async def fake_get(
        self: httpx.AsyncClient, url: str, **kw: object
    ) -> httpx.Response:
        request = httpx.Request("GET", url)
        return httpx.Response(500, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    assert await inventory.fetch() is None
