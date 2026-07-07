import httpx

from app.main import app
from app.services import qr

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_qr_png_bytes() -> None:
    data = qr.qr_png("https://app.example.jp/p/ABC-100")
    assert data.startswith(PNG_MAGIC)


def test_urls() -> None:
    assert qr.product_url("ABC-100").endswith("/p/ABC-100")
    assert qr.quote_url("2026-00042").endswith("/q/2026-00042")


async def test_qr_endpoints() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        for path in ("/api/v1/qr/p/ABC-100.png", "/api/v1/qr/q/2026-00042.png"):
            r = await c.get(path)
            assert r.status_code == 200
            assert r.headers["content-type"] == "image/png"
            assert r.content.startswith(PNG_MAGIC)
