"""ユーザー管理(S-07・admin)。顧客の凍結解除/凍結、スタッフの担当名・役割。"""

from typing import Any

import aiosqlite

ROLES = ("customer", "staff", "admin")


async def list_users(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    rows = await db.execute_fetchall(
        """
        SELECT id, display_name, email, company_name, contact_label, role,
               is_suspended, created_at,
               (SELECT COUNT(*) FROM quotes q
                 WHERE q.customer_id = app_users.id) AS quote_count
        FROM app_users
        ORDER BY role DESC, created_at DESC
        """
    )
    return [dict(r) for r in rows]


async def set_suspended(
    db: aiosqlite.Connection, user_id: str, suspended: bool
) -> None:
    cur = await db.execute(
        "UPDATE app_users SET is_suspended = ? WHERE id = ?",
        (int(suspended), user_id),
    )
    if cur.rowcount == 0:
        raise ValueError("user not found")


async def set_role(
    db: aiosqlite.Connection,
    user_id: str,
    role: str,
    contact_label: str | None = None,
) -> None:
    if role not in ROLES:
        raise ValueError(f"不正な role: {role}")
    cur = await db.execute(
        "UPDATE app_users SET role = ?, contact_label = ? WHERE id = ?",
        (role, contact_label, user_id),
    )
    if cur.rowcount == 0:
        raise ValueError("user not found")
