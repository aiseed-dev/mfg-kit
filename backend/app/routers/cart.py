from fastapi import APIRouter, HTTPException

from app.core.auth import UserDep
from app.core.db import DbDep
from app.schemas.quote import CartItemIn, CartItemOut

router = APIRouter()


@router.get("/cart")
async def get_cart(db: DbDep, user: UserDep) -> list[CartItemOut]:
    rows = await db.execute_fetchall(
        """
        SELECT p.code, p.name, ci.quantity, ci.spec_note, p.price_note,
               (SELECT path FROM product_photos
                 WHERE product_id = p.id ORDER BY sort_order LIMIT 1) AS photo
        FROM cart_items ci JOIN products p ON p.id = ci.product_id
        WHERE ci.user_id = ?
        ORDER BY ci.added_at
        """,
        (user["id"],),
    )
    return [CartItemOut(**dict(r)) for r in rows]


@router.put("/cart/items/{code}")
async def put_item(code: str, item: CartItemIn, db: DbDep, user: UserDep) -> dict:
    cur = await db.execute(
        """
        INSERT INTO cart_items (user_id, product_id, quantity, spec_note)
        SELECT ?, id, ?, ? FROM products
         WHERE code = ? AND is_public AND is_active
        ON CONFLICT (user_id, product_id) DO UPDATE
           SET quantity = excluded.quantity, spec_note = excluded.spec_note
        """,
        (user["id"], item.quantity, item.spec_note, code),
    )
    if cur.rowcount == 0:
        raise HTTPException(404, detail="product not found")
    return {"ok": True}


@router.delete("/cart/items/{code}", status_code=204)
async def delete_item(code: str, db: DbDep, user: UserDep) -> None:
    await db.execute(
        "DELETE FROM cart_items WHERE user_id = ?"
        " AND product_id = (SELECT id FROM products WHERE code = ?)",
        (user["id"], code),
    )
