import asyncio
import sqlite3
from pathlib import Path

import httpx


async def _request_quote(
    client: httpx.AsyncClient, user: str = "u1", note: str | None = None
) -> dict:
    h = {"X-Test-User": user}
    await client.put("/api/v1/cart/items/DR-100", json={"quantity": 1}, headers=h)
    r = await client.post("/api/v1/quotes", json={"note": note}, headers=h)
    assert r.status_code == 201
    return r.json()


async def test_create_quote(client: httpx.AsyncClient, capsys) -> None:
    q = await _request_quote(client, note="納期は8月中を希望")
    assert q["quote_no"].endswith("-00001")

    # カートは空になり、依頼詳細に品目が移っている
    assert (await client.get("/api/v1/cart")).json() == []
    detail = (await client.get(f"/api/v1/quotes/{q['id']}")).json()
    assert detail["status"] == "requested"
    assert detail["note"] == "納期は8月中を希望"
    assert [i["code"] for i in detail["items"]] == ["DR-100"]

    # 会社へのメール通知(コンソールバックエンド)
    out = capsys.readouterr().out
    assert "【見積依頼】" in out and q["quote_no"] in out

    # 連番が進む
    q2 = await _request_quote(client)
    assert q2["quote_no"].endswith("-00002")


async def test_create_quote_empty_cart(client: httpx.AsyncClient) -> None:
    r = await client.post("/api/v1/quotes", json={})
    assert r.status_code == 400


async def test_numbering_is_serialized(
    client: httpx.AsyncClient, db_path: Path
) -> None:
    """同時依頼でも quote_seq が重複しない(BEGIN IMMEDIATE の直列化)"""
    conn = sqlite3.connect(db_path)
    users = [f"c{i}" for i in range(5)]
    conn.executemany(
        "INSERT INTO app_users (id, display_name) VALUES (?, ?)",
        [(u, u) for u in users],
    )
    conn.commit()
    conn.close()
    for u in users:
        await client.put(
            "/api/v1/cart/items/PT-010",
            json={"quantity": 1},
            headers={"X-Test-User": u},
        )
    results = await asyncio.gather(
        *(
            client.post("/api/v1/quotes", json={}, headers={"X-Test-User": u})
            for u in users
        )
    )
    assert all(r.status_code == 201 for r in results)
    seqs = sorted(int(r.json()["quote_no"].split("-")[1]) for r in results)
    assert seqs == [1, 2, 3, 4, 5]


async def test_authorization(client: httpx.AsyncClient) -> None:
    q = await _request_quote(client, user="u1")
    h2 = {"X-Test-User": "u2"}
    assert (
        await client.get(f"/api/v1/quotes/{q['id']}", headers=h2)
    ).status_code == 404
    r = await client.patch(
        f"/api/v1/quotes/{q['id']}", json={"status": "cancelled"}, headers=h2
    )
    assert r.status_code == 404
    assert (await client.get("/api/v1/quotes", headers=h2)).json() == []


async def test_status_transitions(client: httpx.AsyncClient) -> None:
    q = await _request_quote(client)
    # requested からの発注意向は可(会社によるので制限しない)
    r = await client.patch(f"/api/v1/quotes/{q['id']}", json={"status": "ordered"})
    assert r.status_code == 200
    assert r.json()["status"] == "ordered"
    assert r.json()["ordered_at"] is not None

    # 終端(ordered は進行中ではない)からの変更は 409
    r = await client.patch(f"/api/v1/quotes/{q['id']}", json={"status": "cancelled"})
    assert r.status_code == 409

    # 不正な値は 422
    q2 = await _request_quote(client)
    r = await client.patch(f"/api/v1/quotes/{q2['id']}", json={"status": "closed"})
    assert r.status_code == 422


async def test_quote_by_no(client: httpx.AsyncClient) -> None:
    q = await _request_quote(client)
    r = await client.get(f"/api/v1/quotes/by-no/{q['quote_no']}")
    assert r.status_code == 200
    assert r.json()["id"] == q["id"]
    r = await client.get(
        f"/api/v1/quotes/by-no/{q['quote_no']}", headers={"X-Test-User": "u2"}
    )
    assert r.status_code == 404


async def test_list_quotes(client: httpx.AsyncClient) -> None:
    q1 = await _request_quote(client)
    await _request_quote(client)
    rows = (await client.get("/api/v1/quotes")).json()
    assert len(rows) == 2
    assert rows[0]["quote_no"] > rows[1]["quote_no"]  # 新しい順
    assert rows[1]["id"] == q1["id"]
