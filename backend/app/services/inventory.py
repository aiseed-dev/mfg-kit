"""在庫・価格の基幹API中継(S-04)。本システムは保存しない(表示のみ)。

基幹側の最小API: GET {KIKAN_URL}/inventory → [{code, qty, price?}, ...]
KIKAN_URL 未設定(基幹が無い会社)や不応答時は None → 画面は「要見積」表示。
"""

from typing import Any

import httpx

from app.core.config import settings


async def fetch() -> dict[str, dict[str, Any]] | None:
    """製品コード → {qty, price?}。取得できなければ None"""
    if not settings.kikan_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{settings.kikan_url}/inventory")
            r.raise_for_status()
    except httpx.HTTPError:
        return None
    return {row["code"]: row for row in r.json()}
