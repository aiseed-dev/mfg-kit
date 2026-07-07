import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

import asyncpg
from fastapi import Depends

from app.core.config import settings

_pool: asyncpg.Pool | None = None
_lock = asyncio.Lock()


async def _init_conn(conn: asyncpg.Connection) -> None:
    # JSONB を dict / list として読み書きする
    for typ in ("json", "jsonb"):
        await conn.set_type_codec(
            typ, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        async with _lock:
            if _pool is None:
                _pool = await asyncpg.create_pool(
                    settings.database_url, init=_init_conn
                )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_db() -> AsyncIterator[asyncpg.Connection]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


# ルーターの引数はこれを使う: `db: DbDep`
DbDep = Annotated[asyncpg.Connection, Depends(get_db)]
