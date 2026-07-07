import httpx


async def test_cart_flow(client: httpx.AsyncClient) -> None:
    r = await client.put(
        "/api/v1/cart/items/DR-100", json={"quantity": 2, "spec_note": "白"}
    )
    assert r.status_code == 200
    r = await client.put("/api/v1/cart/items/MC-300", json={"quantity": 1})
    assert r.status_code == 200

    r = await client.get("/api/v1/cart")
    items = r.json()
    assert [(i["code"], i["quantity"]) for i in items] == [("DR-100", 2), ("MC-300", 1)]
    assert items[0]["spec_note"] == "白"

    # 数量変更は同じ PUT(upsert)
    r = await client.put("/api/v1/cart/items/DR-100", json={"quantity": 5})
    items = (await client.get("/api/v1/cart")).json()
    assert items[0]["quantity"] == 5

    r = await client.delete("/api/v1/cart/items/DR-100")
    assert r.status_code == 204
    assert len((await client.get("/api/v1/cart")).json()) == 1


async def test_cart_validation(client: httpx.AsyncClient) -> None:
    r = await client.put("/api/v1/cart/items/XX-999", json={"quantity": 1})
    assert r.status_code == 404
    r = await client.put("/api/v1/cart/items/DR-100", json={"quantity": 0})
    assert r.status_code == 422


async def test_cart_is_per_user(client: httpx.AsyncClient) -> None:
    await client.put("/api/v1/cart/items/DR-100", json={"quantity": 1})
    r = await client.get("/api/v1/cart", headers={"X-Test-User": "u2"})
    assert r.json() == []
