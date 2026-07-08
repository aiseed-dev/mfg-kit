from pathlib import Path

import aiosqlite
import pytest

from app.core.db import connect
from app.services import users


@pytest.fixture
async def db(db_path: Path) -> aiosqlite.Connection:
    conn = await connect(str(db_path))
    yield conn
    await conn.close()


async def test_list_users_includes_seed_users(db: aiosqlite.Connection) -> None:
    rows = await users.list_users(db)
    ids = {r["id"] for r in rows}
    assert {"u1", "u2", "s1", "s2"} <= ids


async def test_set_suspended(db: aiosqlite.Connection) -> None:
    await users.set_suspended(db, "u1", True)
    rows = await users.list_users(db)
    row = next(r for r in rows if r["id"] == "u1")
    assert row["is_suspended"] == 1

    await users.set_suspended(db, "u1", False)
    rows = await users.list_users(db)
    row = next(r for r in rows if r["id"] == "u1")
    assert row["is_suspended"] == 0


async def test_set_suspended_not_found(db: aiosqlite.Connection) -> None:
    with pytest.raises(ValueError):
        await users.set_suspended(db, "no-such-id", True)


async def test_set_role(db: aiosqlite.Connection) -> None:
    await users.set_role(db, "u2", "staff", "営業")
    rows = await users.list_users(db)
    row = next(r for r in rows if r["id"] == "u2")
    assert row["role"] == "staff"
    assert row["contact_label"] == "営業"


async def test_set_role_invalid_role(db: aiosqlite.Connection) -> None:
    with pytest.raises(ValueError):
        await users.set_role(db, "u2", "x", "営業")


async def test_set_role_not_found(db: aiosqlite.Connection) -> None:
    with pytest.raises(ValueError):
        await users.set_role(db, "no-such-id", "staff", "営業")
