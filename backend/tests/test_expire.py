import sqlite3
from pathlib import Path

import aiosqlite
import httpx
import pytest

from app.core.db import connect
from app.jobs.expire import run


@pytest.fixture
async def db(db_path: Path) -> aiosqlite.Connection:
    conn = await connect(str(db_path))
    yield conn
    await conn.close()


async def test_expire(
    client: httpx.AsyncClient, db: aiosqlite.Connection, db_path: Path, capsys
) -> None:
    # 新しい依頼(u1)と、20日前の依頼(u2)を用意
    await client.put("/api/v1/cart/items/DR-100", json={"quantity": 1})
    fresh = (await client.post("/api/v1/quotes", json={})).json()

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO quotes (id, customer_id, quote_no, quote_year, quote_seq,
                            created_at)
        VALUES ('old-q', 'u2', '2026-90001', 2026, 90001,
                strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-20 days'))
        """
    )
    conn.commit()
    conn.close()
    capsys.readouterr()

    expired = await run(db)
    assert [q["quote_no"] for q in expired] == ["2026-90001"]

    out = capsys.readouterr().out
    assert "【見積依頼の期限切れ】" in out and "suzuki@example.jp" in out
    assert "【自動クローズ】" in out

    cur = await db.execute("SELECT status FROM quotes WHERE id = 'old-q'")
    assert (await cur.fetchone())[0] == "expired"
    # 新しい依頼は触らない
    r = await client.get(f"/api/v1/quotes/{fresh['id']}")
    assert r.json()["status"] == "requested"

    # 2回目は対象なし
    assert await run(db) == []
