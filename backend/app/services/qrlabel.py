"""QRラベルの面付けPDF(S-06)。銘板・現物・紙カタログ用。

A4 に 4列×6行(48×45mm 相当)。ラベルは QR+型番+製品名。
QR の飛び先は製品ページ(services/qr と同じ URL)。
"""

import io
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.services import qr

COLS, ROWS = 4, 6
MARGIN = 12 * mm
FONT = "HeiseiKakuGo-W5"  # 日本語CIDフォント(埋め込み不要・Webフォント非該当)


def build_pdf(products: list[dict[str, str]], outdir: Path | None = None) -> Path:
    """products: [{code, name}, ...] の選択分を面付けして PDF を書き出す"""
    pdfmetrics.registerFont(UnicodeCIDFont(FONT))
    outdir = outdir or Path(settings.export_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"QRラベル-{datetime.now().strftime('%Y%m%d-%H%M')}.pdf"

    page_w, page_h = A4
    cell_w = (page_w - MARGIN * 2) / COLS
    cell_h = (page_h - MARGIN * 2) / ROWS
    qr_size = min(cell_w, cell_h) - 16 * mm

    c = canvas.Canvas(str(path), pagesize=A4)
    for i, p in enumerate(products):
        pos = i % (COLS * ROWS)
        if i and pos == 0:
            c.showPage()
        col, row = pos % COLS, pos // COLS
        x = MARGIN + col * cell_w
        y = page_h - MARGIN - (row + 1) * cell_h

        png = qr.qr_png(qr.product_url(p["code"]))
        c.drawImage(
            ImageReader(io.BytesIO(png)),
            x + (cell_w - qr_size) / 2,
            y + 12 * mm,
            qr_size,
            qr_size,
        )
        c.setFont(FONT, 9)
        c.drawCentredString(x + cell_w / 2, y + 8 * mm, p["code"])
        c.setFont(FONT, 7)
        name = p["name"][:20]
        c.drawCentredString(x + cell_w / 2, y + 4.5 * mm, name)
    c.save()
    return path
