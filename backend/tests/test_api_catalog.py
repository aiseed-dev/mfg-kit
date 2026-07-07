import httpx


async def test_categories(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/categories")
    assert r.status_code == 200
    assert [c["slug"] for c in r.json()] == ["door", "machine", "parts"]


async def test_products(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/products")
    assert r.status_code == 200
    items = r.json()
    assert [p["code"] for p in items] == ["DR-100", "DR-200", "MC-300", "PT-010"]
    assert items[0]["category_slug"] == "door"
    assert items[0]["specs"]["本体材質"] == "アルミ+断熱材"


async def test_products_filters(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/products", params={"category": "door"})
    assert [p["code"] for p in r.json()] == ["DR-100", "DR-200"]

    r = await client.get("/api/v1/products", params={"q": "供給"})
    assert [p["code"] for p in r.json()] == ["MC-300", "PT-010"]


async def test_product_detail(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/products/DR-100")
    assert r.status_code == 200
    p = r.json()
    assert p["name"] == "断熱玄関ドア 片開き"
    assert p["category_name"] == "玄関ドア"
    assert p["specs"]["断熱性能"] == "H-4等級相当"
    assert p["photos"] == []

    r = await client.get("/api/v1/products/XX-999")
    assert r.status_code == 404
