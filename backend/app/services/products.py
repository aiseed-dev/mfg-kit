"""製品管理(S-03)。staff/ から呼ぶ。保存・公開切替で静的カタログを再生成。"""

import json
import uuid
from typing import Any

import aiosqlite

from app.services import staticgen


async def list_products(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """管理用一覧(非公開・無効も含む)"""
    rows = await db.execute_fetchall(
        """
        SELECT p.id, p.code, p.name, c.slug AS category_slug,
               c.name AS category_name, p.summary, p.price_note,
               p.is_public, p.is_active, p.updated_at
        FROM products p JOIN categories c ON c.id = p.category_id
        ORDER BY p.code
        """
    )
    return [dict(r) for r in rows]


async def get_product(db: aiosqlite.Connection, code: str) -> dict[str, Any] | None:
    cur = await db.execute(
        """
        SELECT p.*, c.slug AS category_slug
        FROM products p JOIN categories c ON c.id = p.category_id
        WHERE p.code = ?
        """,
        (code,),
    )
    row = await cur.fetchone()
    if row is None:
        return None
    d = dict(row)
    d["specs"] = json.loads(d["specs"])
    return d


async def list_categories(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    rows = await db.execute_fetchall(
        "SELECT id, slug, name, sort_order FROM categories ORDER BY sort_order"
    )
    return [dict(r) for r in rows]


async def save_product(
    db: aiosqlite.Connection, data: dict[str, Any], regen_site: bool = True
) -> str:
    """追加・編集(upsert。キーは code)。保存後に静的カタログ再生成。
    data: {code, name, category_slug, summary?, description?,
           specs: dict, price_note?, is_public?, is_active?}"""
    specs = json.dumps(data.get("specs", {}), ensure_ascii=False)
    cur = await db.execute(
        """
        UPDATE products SET name = ?,
               category_id = (SELECT id FROM categories WHERE slug = ?),
               summary = ?, description = ?, specs = ?, price_note = ?,
               is_public = ?, is_active = ?
        WHERE code = ?
        """,
        (
            data["name"],
            data["category_slug"],
            data.get("summary"),
            data.get("description"),
            specs,
            data.get("price_note"),
            int(data.get("is_public", True)),
            int(data.get("is_active", True)),
            data["code"],
        ),
    )
    if cur.rowcount == 0:
        await db.execute(
            """
            INSERT INTO products (id, code, name, category_id, summary,
                                  description, specs, price_note,
                                  is_public, is_active)
            VALUES (?, ?, ?, (SELECT id FROM categories WHERE slug = ?),
                    ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                data["code"],
                data["name"],
                data["category_slug"],
                data.get("summary"),
                data.get("description"),
                specs,
                data.get("price_note"),
                int(data.get("is_public", True)),
                int(data.get("is_active", True)),
            ),
        )
    if regen_site:
        await staticgen.regen()
    return data["code"]


async def set_public(
    db: aiosqlite.Connection, code: str, is_public: bool, regen_site: bool = True
) -> None:
    cur = await db.execute(
        "UPDATE products SET is_public = ? WHERE code = ?",
        (int(is_public), code),
    )
    if cur.rowcount == 0:
        raise ValueError("product not found")
    if regen_site:
        await staticgen.regen()
