import json
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated, Any

import aiosqlite
import httpx
import pytest
from fastapi import Header, HTTPException

from app.core import auth
from app.core.config import settings
from app.core.db import DbDep
from app.main import app
from app.services.seed import seed

ROOT = Path(__file__).parents[2]

# テストユーザー(認証は X-Test-User ヘッダーで差し替え。既定 u1)
USERS = [
    ("u1", "田中", "取引先A", None, "customer"),
    ("u2", "鈴木", "取引先B", None, "customer"),
    ("s1", "山本", None, "営業", "staff"),
]


@pytest.fixture(autouse=True)
def _clear_auth_cache() -> None:
    auth._cache.clear()


@pytest.fixture
async def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """schema 適用+sample.json+テストユーザー投入済みの DB"""
    path = tmp_path / "test.db"
    conn = sqlite3.connect(path)
    conn.executescript((ROOT / "db" / "schema.sql").read_text())
    conn.executemany(
        "INSERT INTO app_users (id, display_name, company_name, contact_label,"
        " role) VALUES (?, ?, ?, ?, ?)",
        USERS,
    )
    conn.commit()
    conn.close()

    data = json.loads((ROOT / "site" / "sample.json").read_text())
    async with aiosqlite.connect(path) as db:
        await seed(db, data)

    monkeypatch.setattr(settings, "db_path", str(path))
    monkeypatch.setattr(settings, "files_dir", str(tmp_path / "files"))
    monkeypatch.setattr(settings, "mail_backend", "console")
    return path


async def _test_user(
    db: DbDep, x_test_user: Annotated[str, Header()] = "u1"
) -> dict[str, Any]:
    cur = await db.execute("SELECT * FROM app_users WHERE id = ?", (x_test_user,))
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(401)
    return dict(row)


@pytest.fixture
async def client(db_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    """認証をテストユーザーに差し替えた API クライアント"""
    app.dependency_overrides[auth.current_user] = _test_user
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        yield c
    app.dependency_overrides.clear()
