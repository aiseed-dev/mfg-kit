from pathlib import Path

from app.services import qrlabel

PRODUCTS = [
    {"code": "DR-100", "name": "断熱玄関ドア 片開き"},
    {"code": "MC-300", "name": "部品整列供給機"},
]


def test_build_pdf(tmp_path: Path) -> None:
    path = qrlabel.build_pdf(PRODUCTS, outdir=tmp_path)
    assert path.exists()
    assert path.suffix == ".pdf"
    assert path.read_bytes()[:5] == b"%PDF-"


def test_build_pdf_over_one_page(tmp_path: Path) -> None:
    """1ページ24枠(4列×6行)を超える25件でもエラーなく生成できる"""
    many = [{"code": f"PT-{i:03d}", "name": f"テスト部品{i}"} for i in range(25)]
    path = qrlabel.build_pdf(many, outdir=tmp_path)
    assert path.exists()
    assert path.read_bytes()[:5] == b"%PDF-"
