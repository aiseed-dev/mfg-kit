"""見積依頼の作成・メッセージ追加(顧客API と staff/ の両方から使う)。"""

import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite

from app.services import mail

JST = ZoneInfo("Asia/Tokyo")

NOW_SQL = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"


class EmptyCartError(Exception):
    pass


async def create_quote(
    db: aiosqlite.Connection, customer: dict[str, Any], note: str | None
) -> dict[str, Any]:
    """カートを quote に変換し、quote_no を採番する。

    採番は BEGIN IMMEDIATE で書き込みロックを取ってから MAX+1
    (DB全体の通し番号・年+連番。quote_no の UNIQUE が安全網)。
    """
    await db.execute("BEGIN IMMEDIATE")
    try:
        items = await db.execute_fetchall(
            """
            SELECT ci.product_id, ci.quantity, ci.spec_note, p.code, p.name
            FROM cart_items ci JOIN products p ON p.id = ci.product_id
            WHERE ci.user_id = ?
            """,
            (customer["id"],),
        )
        if not items:
            raise EmptyCartError
        year = datetime.now(JST).year
        cur = await db.execute(
            "SELECT COALESCE(MAX(quote_seq), 0) + 1 FROM quotes WHERE quote_year = ?",
            (year,),
        )
        seq = (await cur.fetchone())[0]
        quote_no = f"{year}-{seq:05d}"
        qid = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO quotes (id, customer_id, quote_no, quote_year,"
            " quote_seq, note) VALUES (?, ?, ?, ?, ?, ?)",
            (qid, customer["id"], quote_no, year, seq, note),
        )
        await db.executemany(
            "INSERT INTO quote_items (quote_id, product_id, quantity, spec_note)"
            " VALUES (?, ?, ?, ?)",
            [(qid, i["product_id"], i["quantity"], i["spec_note"]) for i in items],
        )
        await db.execute("DELETE FROM cart_items WHERE user_id = ?", (customer["id"],))
        await db.execute("COMMIT")
    except BaseException:
        await db.execute("ROLLBACK")
        raise

    mail.quote_requested(quote_no, customer, [dict(i) for i in items], note)
    return {"id": qid, "quote_no": quote_no}


async def add_message(
    db: aiosqlite.Connection,
    quote_id: str,
    quote_no: str,
    sender: dict[str, Any],
    body: str,
    file_path: str | None = None,
) -> str:
    """メッセージを追加し、相手側へ即時メール通知(顧客→会社)。
    会社→顧客の通知は staff 側の回答関数(Phase 4)が顧客宛に送る。"""
    mid = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO messages (id, quote_id, sender_id, body, file_path)"
        " VALUES (?, ?, ?, ?, ?)",
        (mid, quote_id, sender["id"], body, file_path),
    )
    mail.message_received(quote_no, sender, body)
    return mid
