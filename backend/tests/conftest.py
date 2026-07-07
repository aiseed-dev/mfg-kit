import json
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path

import aiosqlite
import httpx
import pytest

from app.core.config import settings
from app.main import app
from app.services.seed import seed

ROOT = Path(__file__).parents[2]


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[httpx.AsyncClient]:
    """schema.sql 適用+sample.json 投入済みの DB を持つ API クライアント"""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript((ROOT / "db" / "schema.sql").read_text())
    conn.close()

    data = json.loads((ROOT / "site" / "sample.json").read_text())
    async with aiosqlite.connect(db_path) as db:
        await seed(db, data)

    monkeypatch.setattr(settings, "db_path", str(db_path))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        yield c
