import json
from pathlib import Path

from app.services.staticgen import SITE_DIR, build

SAMPLE = json.loads((SITE_DIR / "sample.json").read_text())


def test_build(tmp_path: Path) -> None:
    build(SAMPLE["company"], SAMPLE["categories"], SAMPLE["products"], tmp_path)

    index = (tmp_path / "index.html").read_text()
    assert SAMPLE["company"]["name"] in index

    product = (tmp_path / "p/DR-100/index.html").read_text()
    assert "断熱玄関ドア" in product
    assert "見積を依頼する" in product
    assert "/p/DR-100" in product  # 顧客アプリへの導線

    catalog = json.loads((tmp_path / "catalog.json").read_text())
    assert {c["slug"] for c in catalog["categories"]} == {"door", "machine", "parts"}
    assert len(catalog["products"]) == 4
    # 在庫・価格の数値は含めない(価格表記の文字列のみ)
    assert "qty" not in json.dumps(catalog)

    assert (tmp_path / "c/door/index.html").exists()
    assert (tmp_path / "style.css").exists()
