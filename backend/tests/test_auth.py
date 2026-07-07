"""current_user 本体のテスト(PocketBase は httpx.MockTransport で模擬)"""

from pathlib import Path

import aiosqlite
import httpx
import pytest
from fastapi import HTTPException

from app.core import auth
from app.core.db import connect

PB_RECORD = {"id": "pb-x1", "email": "sato@example.jp", "name": "佐藤"}


def _mock_pb() -> httpx.AsyncClient:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.headers.get("Authorization") == "Bearer good":
            return httpx.Response(200, json={"record": PB_RECORD, "token": "good"})
        return httpx.Response(401, json={})

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://pb"
    )


@pytest.fixture
async def db(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> aiosqlite.Connection:
    monkeypatch.setattr(auth, "_http", _mock_pb())
    conn = await connect(str(db_path))
    yield conn
    await conn.close()


async def test_creates_app_user(db: aiosqlite.Connection) -> None:
    user = await auth.current_user(db, authorization="Bearer good")
    assert user["id"] == "pb-x1"
    assert user["display_name"] == "佐藤"
    assert user["role"] == "customer"

    # 2回目はキャッシュ+既存行(重複作成しない)
    user = await auth.current_user(db, authorization="Bearer good")
    cur = await db.execute("SELECT COUNT(*) FROM app_users WHERE id = 'pb-x1'")
    assert (await cur.fetchone())[0] == 1


async def test_rejects(db: aiosqlite.Connection) -> None:
    for bad in (None, "x", "Bearer bad"):
        with pytest.raises(HTTPException) as e:
            await auth.current_user(db, authorization=bad)
        assert e.value.status_code == 401


async def test_suspended(db: aiosqlite.Connection) -> None:
    await auth.current_user(db, authorization="Bearer good")
    await db.execute("UPDATE app_users SET is_suspended = 1 WHERE id = 'pb-x1'")
    auth._cache.clear()
    with pytest.raises(HTTPException) as e:
        await auth.current_user(db, authorization="Bearer good")
    assert e.value.status_code == 403
