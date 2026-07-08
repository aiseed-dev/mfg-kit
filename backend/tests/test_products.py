from pathlib import Path

import aiosqlite
import httpx
import pytest

from app.core.db import connect
from app.services import products


@pytest.fixture
async def db(db_path: Path) -> aiosqlite.Connection:
    conn = await connect(str(db_path))
    yield conn
    await conn.close()


NEW_PRODUCT = {
    "code": "MC-999",
    "name": "新型省力機械",
    "category_slug": "machine",
    "summary": "テスト用の新規製品",
    "description": "説明文",
    "specs": {"電源": "AC200V"},
    "price_note": "要見積",
}


async def test_save_and_get_product(db: aiosqlite.Connection) -> None:
    before = await products.list_products(db)

    await products.save_product(db, NEW_PRODUCT, regen_site=False)

    got = await products.get_product(db, "MC-999")
    assert got is not None
    assert got["name"] == "新型省力機械"
    assert got["specs"] == {"電源": "AC200V"}  # dict で返る
    assert got["category_slug"] == "machine"

    after = await products.list_products(db)
    assert len(after) == len(before) + 1


async def test_save_product_upserts_by_code(db: aiosqlite.Connection) -> None:
    await products.save_product(db, NEW_PRODUCT, regen_site=False)
    before = await products.list_products(db)

    updated = {**NEW_PRODUCT, "name": "新型省力機械(改良版)"}
    await products.save_product(db, updated, regen_site=False)

    after = await products.list_products(db)
    assert len(after) == len(before)  # 件数は増えない(更新)

    got = await products.get_product(db, "MC-999")
    assert got["name"] == "新型省力機械(改良版)"


async def test_list_categories(db: aiosqlite.Connection) -> None:
    cats = await products.list_categories(db)
    slugs = [c["slug"] for c in cats]
    assert slugs == ["door", "machine", "parts"]  # sort_order 順


async def test_set_public_hides_from_public_api(
    db: aiosqlite.Connection, client: httpx.AsyncClient
) -> None:
    codes_before = [p["code"] for p in (await client.get("/api/v1/products")).json()]
    assert "DR-100" in codes_before

    await products.set_public(db, "DR-100", False, regen_site=False)

    codes_after = [p["code"] for p in (await client.get("/api/v1/products")).json()]
    assert "DR-100" not in codes_after

    r = await client.get("/api/v1/products/DR-100")
    assert r.status_code == 404


async def test_set_public_not_found(db: aiosqlite.Connection) -> None:
    with pytest.raises(ValueError):
        await products.set_public(db, "NO-SUCH-CODE", False, regen_site=False)
