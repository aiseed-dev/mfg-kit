import io

import segno

from app.core.config import settings


def qr_png(url: str) -> bytes:
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="png", scale=6, border=2)
    return buf.getvalue()


def product_url(code: str) -> str:
    """製品QRの飛び先(銘板・紙カタログ→顧客アプリ /p/{code})"""
    return f"{settings.app_base_url}/p/{code}"


def quote_url(quote_no: str) -> str:
    """見積番号QRの飛び先(見積書・納品書→顧客アプリ /q/{quote_no})"""
    return f"{settings.app_base_url}/q/{quote_no}"
