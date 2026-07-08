"""requested 放置(既定14日)の expired 自動クローズ+通知(02_api)。

systemd timer で日次実行: python -m app.jobs.expire
アプリ内スケジューラは使わない(再起動・多重起動の考慮を消す。DESIGN)。
"""

import asyncio
from typing import Any

import aiosqlite

from app.core.config import settings
from app.core.db import connect
from app.services import mail


async def run(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    days = int(settings.expire_days)
    rows = await db.execute_fetchall(
        f"""
        SELECT q.id, q.quote_no, u.email AS customer_email
        FROM quotes q JOIN app_users u ON u.id = q.customer_id
        WHERE q.status = 'requested'
          AND q.created_at < strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-{days} days')
        """
    )
    expired = [dict(r) for r in rows]
    for q in expired:
        await db.execute(
            "UPDATE quotes SET status = 'expired' WHERE id = ?", (q["id"],)
        )
        if q["customer_email"]:
            mail.send(
                q["customer_email"],
                f"【見積依頼の期限切れ】{q['quote_no']}",
                f"見積依頼 {q['quote_no']} は {days} 日間回答がなかったため"
                "クローズされました。\n引き続きご希望の場合は、お手数ですが"
                "再度ご依頼ください。",
            )
    if expired:
        nos = "\n".join(f"- {q['quote_no']}" for q in expired)
        mail.send(
            settings.company_mail_to,
            f"【自動クローズ】期限切れ {len(expired)} 件",
            f"回答のないまま {days} 日経過した依頼をクローズしました:\n{nos}",
        )
    return expired


async def main() -> None:
    db = await connect()
    try:
        expired = await run(db)
    finally:
        await db.close()
    print(f"ok: {len(expired)} 件を expired にした")


if __name__ == "__main__":
    asyncio.run(main())
