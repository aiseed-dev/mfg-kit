from fastapi import APIRouter, Response

from app.services import qr

router = APIRouter()

CACHE = {"Cache-Control": "public, max-age=86400"}


@router.get("/qr/p/{code}.png")
async def product_qr(code: str) -> Response:
    return Response(
        qr.qr_png(qr.product_url(code)), media_type="image/png", headers=CACHE
    )


@router.get("/qr/q/{quote_no}.png")
async def quote_qr(quote_no: str) -> Response:
    return Response(
        qr.qr_png(qr.quote_url(quote_no)), media_type="image/png", headers=CACHE
    )
