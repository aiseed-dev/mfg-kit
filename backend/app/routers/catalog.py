import json

from fastapi import APIRouter, HTTPException

from app.core.db import DbDep
from app.schemas.catalog import CategoryOut, ProductCard, ProductDetail

router = APIRouter()


@router.get("/categories")
async def list_categories(db: DbDep) -> list[CategoryOut]:
    rows = await db.execute_fetchall(
        "SELECT slug, name, sort_order FROM categories ORDER BY sort_order"
    )
    return [CategoryOut(**dict(r)) for r in rows]


@router.get("/products")
async def list_products(
    db: DbDep,
    category: str | None = None,
    q: str | None = None,
) -> list[ProductCard]:
    sql = """
        SELECT p.code, p.name, p.summary, p.specs, p.price_note,
               c.slug AS category_slug,
               (SELECT path FROM product_photos
                 WHERE product_id = p.id ORDER BY sort_order LIMIT 1) AS photo
        FROM products p
        JOIN categories c ON c.id = p.category_id
        WHERE p.is_public AND p.is_active
    """
    args: list[str] = []
    if category:
        sql += " AND c.slug = ?"
        args.append(category)
    if q:
        sql += " AND (p.name LIKE ? OR p.code LIKE ? OR p.summary LIKE ?)"
        args += [f"%{q}%"] * 3
    sql += " ORDER BY p.code"
    rows = await db.execute_fetchall(sql, args)
    return [ProductCard(**{**dict(r), "specs": json.loads(r["specs"])}) for r in rows]


@router.get("/products/{code}")
async def get_product(code: str, db: DbDep) -> ProductDetail:
    cur = await db.execute(
        """
        SELECT p.code, p.name, p.summary, p.description, p.specs, p.price_note,
               c.slug AS category_slug, c.name AS category_name,
               COALESCE((SELECT json_group_array(path) FROM
                          (SELECT path FROM product_photos
                            WHERE product_id = p.id ORDER BY sort_order)),
                        '[]') AS photos
        FROM products p
        JOIN categories c ON c.id = p.category_id
        WHERE p.code = ? AND p.is_public AND p.is_active
        """,
        (code,),
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(404, detail="product not found")
    return ProductDetail(
        **{
            **dict(row),
            "specs": json.loads(row["specs"]),
            "photos": json.loads(row["photos"]),
        }
    )
