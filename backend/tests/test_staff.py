from pathlib import Path

import aiosqlite
import httpx
import pytest

from app.core.db import connect
from app.services import staff

S1 = {"id": "s1", "display_name": "山本", "role": "staff"}


async def _quote(client: httpx.AsyncClient, user: str = "u1") -> dict:
    h = {"X-Test-User": user}
    await client.put("/api/v1/cart/items/MC-300", json={"quantity": 1}, headers=h)
    return (await client.post("/api/v1/quotes", json={}, headers=h)).json()


@pytest.fixture
async def db(db_path: Path) -> aiosqlite.Connection:
    conn = await connect(str(db_path))
    yield conn
    await conn.close()


async def test_answer_flow(
    client: httpx.AsyncClient, db: aiosqlite.Connection, capsys
) -> None:
    q = await _quote(client)
    capsys.readouterr()  # 依頼受付メールを読み捨て

    assert (await staff.dashboard(db))["open_count"] == 1

    await staff.answer(db, q["id"], S1, "お見積り: 180万円、納期10週間")
    out = capsys.readouterr().out
    assert "【見積回答】" in out and "tanaka@example.jp" in out

    detail = await staff.quote_detail(db, q["id"], S1)
    assert detail["status"] == "answered"
    assert detail["answered_by"] == "s1"
    first_answered_at = detail["answered_at"]
    assert first_answered_at is not None

    # 顧客側から見ると回答が届いている
    msgs = (await client.get(f"/api/v1/quotes/{q['id']}/messages")).json()
    assert msgs[-1]["is_mine"] is False
    assert "180万円" in msgs[-1]["body"]

    # 追い回答しても担当者・回答日時は初回のまま
    await staff.answer(db, q["id"], {"id": "s2", "display_name": "別人"}, "追記です")
    detail = await staff.quote_detail(db, q["id"], S1)
    assert detail["answered_by"] == "s1"
    assert detail["answered_at"] == first_answered_at

    assert (await staff.dashboard(db))["open_count"] == 0


async def test_detail_marks_read(
    client: httpx.AsyncClient, db: aiosqlite.Connection
) -> None:
    q = await _quote(client)
    await client.post(
        f"/api/v1/quotes/{q['id']}/messages", data={"body": "至急お願いします"}
    )
    rows = await staff.list_quotes(db)
    assert rows[0]["unread"] == 1

    await staff.quote_detail(db, q["id"], S1)  # 開いた=既読
    rows = await staff.list_quotes(db)
    assert rows[0]["unread"] == 0


async def test_list_orders_requested_first(
    client: httpx.AsyncClient, db: aiosqlite.Connection
) -> None:
    q1 = await _quote(client)
    q2 = await _quote(client, user="u2")
    await staff.answer(db, q1["id"], S1, "回答済みにする")
    rows = await staff.list_quotes(db)
    assert [r["id"] for r in rows] == [q2["id"], q1["id"]]  # requested が上
    assert rows[0]["company_name"] == "取引先B"


async def test_set_status(client: httpx.AsyncClient, db: aiosqlite.Connection) -> None:
    q = await _quote(client)
    await staff.set_status(db, q["id"], "ordered")
    detail = await staff.quote_detail(db, q["id"], S1)
    ordered_at = detail["ordered_at"]
    assert detail["status"] == "ordered" and ordered_at is not None

    # 完了にしても計上基準(ordered_at)は変わらない
    await staff.set_status(db, q["id"], "closed")
    detail = await staff.quote_detail(db, q["id"], S1)
    assert detail["status"] == "closed"
    assert detail["ordered_at"] == ordered_at

    with pytest.raises(ValueError):
        await staff.set_status(db, q["id"], "requested")
    with pytest.raises(ValueError):
        await staff.answer(db, q["id"], S1, "closed には回答できない")
