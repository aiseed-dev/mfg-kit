from collections.abc import AsyncIterator
from typing import Annotated

import aiosqlite
from fastapi import Depends

from app.core.config import settings


async def connect(path: str | None = None) -> aiosqlite.Connection:
    """設定済みの接続を返す。呼び出し側が close すること。"""
    db = await aiosqlite.connect(path or settings.db_path, isolation_level=None)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA busy_timeout = 5000")
    return db


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    db = await connect()
    try:
        yield db
    finally:
        await db.close()


# ルーターの引数はこれを使う: `db: DbDep`
DbDep = Annotated[aiosqlite.Connection, Depends(get_db)]
