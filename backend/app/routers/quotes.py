from pathlib import Path
from typing import Annotated, Any

import aiosqlite
from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.auth import UserDep
from app.core.config import settings
from app.core.db import DbDep
from app.schemas.quote import (
    MessageCreated,
    MessageOut,
    QuoteCreateIn,
    QuoteDetail,
    QuoteListItem,
    QuotePatchIn,
)
from app.services import quotes as svc
from app.services.quotes import NOW_SQL

router = APIRouter()

# 添付は PDF/画像のみ・10MB まで(02_api)
MAX_FILE = 10 * 1024 * 1024
MAGIC = {
    "pdf": (b"%PDF", "application/pdf"),
    "png": (b"\x89PNG", "image/png"),
    "jpg": (b"\xff\xd8\xff", "image/jpeg"),
}


async def _own_quote(
    db: aiosqlite.Connection, user: dict[str, Any], quote_id: str
) -> aiosqlite.Row:
    cur = await db.execute(
        "SELECT * FROM quotes WHERE id = ? AND customer_id = ?",
        (quote_id, user["id"]),
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(404, detail="quote not found")
    return row


async def _detail(db: aiosqlite.Connection, q: aiosqlite.Row) -> QuoteDetail:
    items = await db.execute_fetchall(
        """
        SELECT p.code, p.name, qi.quantity, qi.spec_note
        FROM quote_items qi JOIN products p ON p.id = qi.product_id
        WHERE qi.quote_id = ? ORDER BY p.code
        """,
        (q["id"],),
    )
    fields = QuoteDetail.model_fields.keys() - {"items"}
    return QuoteDetail(**{k: q[k] for k in fields}, items=[dict(i) for i in items])


@router.post("/quotes", status_code=201)
async def create_quote(body: QuoteCreateIn, db: DbDep, user: UserDep) -> dict:
    try:
        return await svc.create_quote(db, user, body.note)
    except svc.EmptyCartError:
        raise HTTPException(400, detail="カートが空です") from None


@router.get("/quotes")
async def list_quotes(
    db: DbDep,
    user: UserDep,
    cursor: str | None = None,
    limit: int = 20,
) -> list[QuoteListItem]:
    limit = min(limit, 100)
    sql = """
        SELECT q.id, q.quote_no, q.status, q.created_at,
               (SELECT body FROM messages m WHERE m.quote_id = q.id
                 ORDER BY sent_at DESC LIMIT 1) AS last_message,
               (SELECT sent_at FROM messages m WHERE m.quote_id = q.id
                 ORDER BY sent_at DESC LIMIT 1) AS last_message_at
        FROM quotes q WHERE q.customer_id = ?
    """
    args: list[Any] = [user["id"]]
    if cursor:
        sql += " AND q.created_at < ?"
        args.append(cursor)
    sql += " ORDER BY q.created_at DESC LIMIT ?"
    args.append(limit)
    rows = await db.execute_fetchall(sql, args)
    return [QuoteListItem(**dict(r)) for r in rows]


# /quotes/{id} より先に定義すること(パス照合順)
@router.get("/quotes/by-no/{quote_no}")
async def get_quote_by_no(quote_no: str, db: DbDep, user: UserDep) -> QuoteDetail:
    cur = await db.execute(
        "SELECT * FROM quotes WHERE quote_no = ? AND customer_id = ?",
        (quote_no, user["id"]),
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(404, detail="quote not found")
    return await _detail(db, row)


@router.get("/quotes/{quote_id}")
async def get_quote(quote_id: str, db: DbDep, user: UserDep) -> QuoteDetail:
    return await _detail(db, await _own_quote(db, user, quote_id))


@router.patch("/quotes/{quote_id}")
async def patch_quote(
    quote_id: str, body: QuotePatchIn, db: DbDep, user: UserDep
) -> QuoteDetail:
    q = await _own_quote(db, user, quote_id)
    # 進行中(requested/answered)からのみ遷移可。終端からは変更不可(02_api)
    if q["status"] not in ("requested", "answered"):
        raise HTTPException(409, detail=f"{q['status']} からは変更できません")
    await db.execute(
        f"""
        UPDATE quotes SET status = ?,
               ordered_at = CASE WHEN ? = 'ordered' THEN {NOW_SQL}
                            ELSE ordered_at END
        WHERE id = ?
        """,
        (body.status, body.status, quote_id),
    )
    return await _detail(db, await _own_quote(db, user, quote_id))


@router.get("/quotes/{quote_id}/messages")
async def list_messages(quote_id: str, db: DbDep, user: UserDep) -> list[MessageOut]:
    await _own_quote(db, user, quote_id)
    # スレッドを開いた=相手からの未読に既読を付ける(DESIGN)
    await db.execute(
        f"UPDATE messages SET read_at = {NOW_SQL}"
        " WHERE quote_id = ? AND sender_id <> ? AND read_at IS NULL",
        (quote_id, user["id"]),
    )
    rows = await db.execute_fetchall(
        "SELECT id, body, file_path, sent_at, read_at, sender_id"
        " FROM messages WHERE quote_id = ? ORDER BY sent_at",
        (quote_id,),
    )
    return [
        MessageOut(
            id=r["id"],
            body=r["body"],
            has_file=r["file_path"] is not None,
            sent_at=r["sent_at"],
            read_at=r["read_at"],
            is_mine=r["sender_id"] == user["id"],
        )
        for r in rows
    ]


@router.post("/quotes/{quote_id}/messages", status_code=201)
async def post_message(
    quote_id: str,
    db: DbDep,
    user: UserDep,
    body: Annotated[str, Form(min_length=1)],
    file: UploadFile | None = None,
) -> MessageCreated:
    q = await _own_quote(db, user, quote_id)

    if file is not None:
        data = await file.read()
        if len(data) > MAX_FILE:
            raise HTTPException(413, detail="添付は10MBまでです")
        ext = next(
            (e for e, (magic, _) in MAGIC.items() if data.startswith(magic)), None
        )
        if ext is None:
            raise HTTPException(415, detail="添付はPDFまたは画像のみです")
        dest = Path(settings.files_dir) / quote_id
        dest.mkdir(parents=True, exist_ok=True)

    mid = await svc.add_message(db, quote_id, q["quote_no"], user, body, file_path=None)
    if file is not None:
        path = dest / f"{mid}.{ext}"
        path.write_bytes(data)
        await db.execute(
            "UPDATE messages SET file_path = ? WHERE id = ?", (str(path), mid)
        )
    return MessageCreated(id=mid)


@router.get("/quotes/{quote_id}/files/{message_id}")
async def get_file(
    quote_id: str, message_id: str, db: DbDep, user: UserDep
) -> FileResponse:
    await _own_quote(db, user, quote_id)
    cur = await db.execute(
        "SELECT file_path FROM messages WHERE id = ? AND quote_id = ?",
        (message_id, quote_id),
    )
    row = await cur.fetchone()
    if row is None or row["file_path"] is None:
        raise HTTPException(404, detail="file not found")
    path = Path(row["file_path"])
    ext = path.suffix.lstrip(".")
    return FileResponse(path, media_type=MAGIC[ext][1], filename=path.name)
