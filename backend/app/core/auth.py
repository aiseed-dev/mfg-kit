"""PocketBase トークン検証(02_api)。

Bearer トークンを PocketBase の auth-refresh で検証し、初回アクセス時に
app_users を自動作成する。検証結果は TTL 60秒でメモリキャッシュ。
"""

import time
from typing import Annotated, Any

import httpx
from fastapi import Depends, Header, HTTPException

from app.core.config import settings
from app.core.db import DbDep

TTL = 60.0
_cache: dict[str, tuple[float, str]] = {}  # token -> (期限, user_id)
_http: httpx.AsyncClient | None = None


async def _pb() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(base_url=settings.pb_url, timeout=5)
    return _http


async def _verify_token(authorization: str) -> str:
    """PocketBase で検証し user_id を返す。app_users の自動作成用に
    表示名も返したいので (id, display_name, company) のタプル。"""
    pb = await _pb()
    try:
        r = await pb.post(
            "/api/collections/users/auth-refresh",
            headers={"Authorization": authorization},
        )
    except httpx.HTTPError as e:
        raise HTTPException(503, detail="認証サーバーに接続できません") from e
    if r.status_code != 200:
        raise HTTPException(401, detail="トークンが無効です")
    return r.json()["record"]


async def current_user(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="認証が必要です")
    token = authorization.removeprefix("Bearer ")

    now = time.monotonic()
    hit = _cache.get(token)
    if hit and hit[0] > now:
        uid = hit[1]
    else:
        rec = await _verify_token(authorization)
        uid = rec["id"]
        display = rec.get("name") or rec.get("email", "").split("@")[0] or uid
        await db.execute(
            "INSERT INTO app_users (id, display_name, email, company_name)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT (id) DO UPDATE SET email = excluded.email",
            (uid, display, rec.get("email"), rec.get("company")),
        )
        _cache[token] = (now + TTL, uid)

    cur = await db.execute("SELECT * FROM app_users WHERE id = ?", (uid,))
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(401, detail="トークンが無効です")
    if row["is_suspended"]:
        raise HTTPException(403, detail="アカウントが凍結されています")
    return dict(row)


UserDep = Annotated[dict[str, Any], Depends(current_user)]
