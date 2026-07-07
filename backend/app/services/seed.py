"""サンプル/初期データの投入。site/sample.json と同じ形式を受け取る。

CLI: python -m app.services.seed [json_path]
(DB は .env の DB_PATH。事前に scripts/db-init で schema.sql を適用しておく)
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from app.core import db as core_db
from app.services.staticgen import SITE_DIR


async def seed(db: aiosqlite.Connection, data: dict[str, Any]) -> None:
    for c in data["categories"]:
        await db.execute(
            "INSERT INTO categories (slug, name, sort_order) VALUES (?, ?, ?)",
            (c["slug"], c["name"], c["sort_order"]),
        )
    for p in data["products"]:
        pid = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO products (id, code, name, category_id,
                                  summary, description, specs, price_note)
            VALUES (?, ?, ?, (SELECT id FROM categories WHERE slug = ?),
                    ?, ?, ?, ?)
            """,
            (
                pid,
                p["code"],
                p["name"],
                p["category_slug"],
                p.get("summary"),
                p.get("description"),
                json.dumps(p.get("specs", {}), ensure_ascii=False),
                p.get("price_note"),
            ),
        )
        for i, path in enumerate(p.get("photos", [])):
            await db.execute(
                "INSERT INTO product_photos (id, product_id, path, sort_order)"
                " VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), pid, path, i),
            )
    await db.commit()


async def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SITE_DIR / "sample.json"
    data = json.loads(src.read_text())
    db = await core_db.connect()
    try:
        await seed(db, data)
    finally:
        await db.close()
    print(f"ok: {src} を投入した")


if __name__ == "__main__":
    asyncio.run(main())
