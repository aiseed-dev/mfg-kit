"""社内アプリ(staff/ = Flet)が呼ぶ業務ロジック(S-01・S-02)。

公開 API にはこの機能を出さない(02_api「社内機能」)。
Flet の各 view はここの関数を呼ぶだけにする。
"""

import uuid
from typing import Any

import aiosqlite

from app.services import mail
from app.services.quotes import NOW_SQL


async def dashboard(db: aiosqlite.Connection) -> dict[str, Any]:
    """未回答件数(赤バッジ)と直近の依頼"""
    cur = await db.execute("SELECT COUNT(*) FROM quotes WHERE status = 'requested'")
    open_count = (await cur.fetchone())[0]
    recent = await list_quotes(db, limit=10)
    return {"open_count": open_count, "recent": recent}


async def list_quotes(
    db: aiosqlite.Connection, status: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    """見積一覧。requested を上に、新しい順(S-01)"""
    sql = """
        SELECT q.id, q.quote_no, q.status, q.note, q.created_at,
               q.answered_at, q.ordered_at,
               u.display_name AS customer_name, u.company_name,
               (SELECT COUNT(*) FROM messages m
                 WHERE m.quote_id = q.id AND m.sender_id = q.customer_id
                   AND m.read_at IS NULL) AS unread
        FROM quotes q JOIN app_users u ON u.id = q.customer_id
    """
    args: list[Any] = []
    if status:
        sql += " WHERE q.status = ?"
        args.append(status)
    sql += " ORDER BY (q.status = 'requested') DESC, q.created_at DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in await db.execute_fetchall(sql, args)]


async def quote_detail(
    db: aiosqlite.Connection, quote_id: str, viewer: dict[str, Any]
) -> dict[str, Any] | None:
    """依頼詳細(品目・数量・個別仕様・要望+メッセージ)。
    表示した時点で顧客からの未読に既読を付ける(受け手=会社側)。"""
    cur = await db.execute(
        """
        SELECT q.*, u.display_name AS customer_name, u.company_name,
               u.email AS customer_email
        FROM quotes q JOIN app_users u ON u.id = q.customer_id
        WHERE q.id = ?
        """,
        (quote_id,),
    )
    q = await cur.fetchone()
    if q is None:
        return None
    await db.execute(
        f"UPDATE messages SET read_at = {NOW_SQL}"
        " WHERE quote_id = ? AND sender_id = ? AND read_at IS NULL",
        (quote_id, q["customer_id"]),
    )
    items = await db.execute_fetchall(
        """
        SELECT p.code, p.name, qi.quantity, qi.spec_note
        FROM quote_items qi JOIN products p ON p.id = qi.product_id
        WHERE qi.quote_id = ? ORDER BY p.code
        """,
        (quote_id,),
    )
    messages = await db.execute_fetchall(
        """
        SELECT m.id, m.body, m.file_path, m.sent_at, m.read_at,
               m.sender_id, u.display_name AS sender_name
        FROM messages m JOIN app_users u ON u.id = m.sender_id
        WHERE m.quote_id = ? ORDER BY m.sent_at
        """,
        (quote_id,),
    )
    return {
        **dict(q),
        "items": [dict(i) for i in items],
        "messages": [dict(m) for m in messages],
    }


async def answer(
    db: aiosqlite.Connection, quote_id: str, staff: dict[str, Any], body: str
) -> None:
    """回答(金額・納期をメッセージで提示)→ answered。
    担当者(answered_by)と回答日時は初回のみ記録。顧客へ即時メール通知。"""
    cur = await db.execute(
        """
        SELECT q.quote_no, q.status, u.email AS customer_email
        FROM quotes q JOIN app_users u ON u.id = q.customer_id
        WHERE q.id = ?
        """,
        (quote_id,),
    )
    q = await cur.fetchone()
    if q is None:
        raise ValueError("quote not found")
    if q["status"] not in ("requested", "answered"):
        raise ValueError(f"{q['status']} には回答できません")
    await db.execute(
        "INSERT INTO messages (id, quote_id, sender_id, body) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), quote_id, staff["id"], body),
    )
    await db.execute(
        f"""
        UPDATE quotes SET status = 'answered',
               answered_at = COALESCE(answered_at, {NOW_SQL}),
               answered_by = COALESCE(answered_by, ?)
        WHERE id = ?
        """,
        (staff["id"], quote_id),
    )
    if q["customer_email"]:
        mail.quote_answered(q["customer_email"], q["quote_no"], body)


async def set_status(db: aiosqlite.Connection, quote_id: str, status: str) -> None:
    """受注・完了・辞退の管理(S-02)。ordered_at は初回のみ記録
    (台帳の計上基準なので上書きしない)"""
    if status not in ("ordered", "closed", "declined"):
        raise ValueError(f"staff が設定できない status: {status}")
    cur = await db.execute(
        f"""
        UPDATE quotes SET status = ?,
               ordered_at = CASE WHEN ? = 'ordered'
                            THEN COALESCE(ordered_at, {NOW_SQL})
                            ELSE ordered_at END
        WHERE id = ?
        """,
        (status, status, quote_id),
    )
    if cur.rowcount == 0:
        raise ValueError("quote not found")
