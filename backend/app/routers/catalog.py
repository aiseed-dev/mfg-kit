from fastapi import APIRouter, HTTPException

from app.core.db import DbDep
from app.schemas.catalog import CategoryOut, ProductCard, ProductDetail

router = APIRouter()


@router.get("/categories")
async def list_categories(db: DbDep) -> list[CategoryOut]:
    rows = await db.fetch(
        "SELECT slug, name, sort_order FROM mfg.categories ORDER BY sort_order"
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
               (SELECT path FROM mfg.product_photos
                 WHERE product_id = p.id ORDER BY sort_order LIMIT 1) AS photo
        FROM mfg.products p
        JOIN mfg.categories c ON c.id = p.category_id
        WHERE p.is_public AND p.is_active
    """
    args: list[str] = []
    if category:
        args.append(category)
        sql += f" AND c.slug = ${len(args)}"
    if q:
        args.append(f"%{q}%")
        n = len(args)
        sql += f" AND (p.name ILIKE ${n} OR p.code ILIKE ${n} OR p.summary ILIKE ${n})"
    sql += " ORDER BY p.code"
    rows = await db.fetch(sql, *args)
    return [ProductCard(**dict(r)) for r in rows]


@router.get("/products/{code}")
async def get_product(code: str, db: DbDep) -> ProductDetail:
    row = await db.fetchrow(
        """
        SELECT p.code, p.name, p.summary, p.description, p.specs, p.price_note,
               c.slug AS category_slug, c.name AS category_name,
               COALESCE((SELECT json_agg(path ORDER BY sort_order)
                           FROM mfg.product_photos WHERE product_id = p.id),
                        '[]'::json) AS photos
        FROM mfg.products p
        JOIN mfg.categories c ON c.id = p.category_id
        WHERE p.code = $1 AND p.is_public AND p.is_active
        """,
        code,
    )
    if row is None:
        raise HTTPException(404, detail="product not found")
    return ProductDetail(**dict(row))
