import sqlite3
from pathlib import Path

import httpx


async def _quote(client: httpx.AsyncClient) -> dict:
    await client.put("/api/v1/cart/items/DR-100", json={"quantity": 1})
    return (await client.post("/api/v1/quotes", json={})).json()


async def test_message_flow(client: httpx.AsyncClient, db_path: Path, capsys) -> None:
    q = await _quote(client)
    r = await client.post(
        f"/api/v1/quotes/{q['id']}/messages", data={"body": "図面は後送します"}
    )
    assert r.status_code == 201
    assert "【新着メッセージ】" in capsys.readouterr().out

    # 会社側(s1)からの返信を直接投入(staff 経由の想定)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO messages (id, quote_id, sender_id, body)"
        " VALUES ('m-s1', ?, 's1', 'お見積り: 45万円、納期4週間')",
        (q["id"],),
    )
    conn.commit()

    msgs = (await client.get(f"/api/v1/quotes/{q['id']}/messages")).json()
    assert [m["is_mine"] for m in msgs] == [True, False]
    # 自分の送信は相手未読のまま、相手からの分はスレッドを開いた時点で既読
    assert msgs[0]["read_at"] is None
    row = conn.execute("SELECT read_at FROM messages WHERE id = 'm-s1'").fetchone()
    conn.close()
    assert row[0] is not None


async def test_attachment(client: httpx.AsyncClient) -> None:
    q = await _quote(client)
    pdf = b"%PDF-1.4 fake"
    r = await client.post(
        f"/api/v1/quotes/{q['id']}/messages",
        data={"body": "図面を添付します"},
        files={"file": ("zumen.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 201
    mid = r.json()["id"]

    msgs = (await client.get(f"/api/v1/quotes/{q['id']}/messages")).json()
    assert msgs[0]["has_file"]

    r = await client.get(f"/api/v1/quotes/{q['id']}/files/{mid}")
    assert r.status_code == 200
    assert r.content == pdf
    assert r.headers["content-type"] == "application/pdf"

    # 他人はダウンロードできない
    r = await client.get(
        f"/api/v1/quotes/{q['id']}/files/{mid}", headers={"X-Test-User": "u2"}
    )
    assert r.status_code == 404


async def test_attachment_validation(client: httpx.AsyncClient) -> None:
    q = await _quote(client)
    url = f"/api/v1/quotes/{q['id']}/messages"

    r = await client.post(
        url, data={"body": "x"}, files={"file": ("a.exe", b"MZ\x90\x00", None)}
    )
    assert r.status_code == 415

    r = await client.post(
        url,
        data={"body": "x"},
        files={"file": ("big.pdf", b"%PDF" + b"0" * (10 * 1024 * 1024), None)},
    )
    assert r.status_code == 413

    r = await client.post(url, data={"body": ""})
    assert r.status_code == 422
