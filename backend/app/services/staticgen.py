"""公開静的サイトの生成(P-01〜03)。

build() は DB に依存しない純関数(データは dict のリストで受ける)。
DB から読んで呼ぶラッパー(製品保存時+日次の再生成)は Phase 4 で足す。
アップロード(cf-publish で Pages/R2)は生成とは別step。

CLI: python -m app.services.staticgen site/sample.json site/dist
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

SITE_DIR = Path(__file__).parents[3] / "site"

Data = dict[str, Any]


def build(
    company: Data,
    categories: list[Data],
    products: list[Data],
    outdir: Path,
) -> None:
    """categories: {slug,name,sort_order} / products: {code,name,category_slug,
    summary,description,specs,price_note,photos}。公開分のみ渡すこと。"""
    env = Environment(
        loader=FileSystemLoader(SITE_DIR / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    categories = sorted(categories, key=lambda c: c["sort_order"])
    by_cat: dict[str, list[Data]] = {c["slug"]: [] for c in categories}
    for p in sorted(products, key=lambda p: p["code"]):
        by_cat[p["category_slug"]].append(p)
    for c in categories:
        c["count"] = len(by_cat[c["slug"]])

    ctx = {
        "company": company,
        "categories": categories,
        "app_url": settings.app_base_url,
    }
    outdir.mkdir(parents=True, exist_ok=True)

    def render(template: str, dest: str, **kw: Any) -> None:
        path = outdir / dest
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(env.get_template(template).render(**ctx, **kw))

    render("index.html", "index.html", products=products)
    for c in categories:
        render(
            "category.html",
            f"c/{c['slug']}/index.html",
            cat=c,
            products=by_cat[c["slug"]],
        )
        for p in by_cat[c["slug"]]:
            render("product.html", f"p/{p['code']}/index.html", cat=c, p=p)

    shutil.copy(SITE_DIR / "static" / "style.css", outdir / "style.css")

    # 顧客アプリのカタログ系 Widget が読む JSON(在庫・価格は含めない)
    catalog = {
        "categories": [
            {k: c[k] for k in ("slug", "name", "sort_order")} for c in categories
        ],
        "products": [
            {
                "code": p["code"],
                "name": p["name"],
                "category_slug": p["category_slug"],
                "summary": p.get("summary"),
                "description": p.get("description"),
                "specs": p.get("specs", {}),
                "price_note": p.get("price_note"),
                "photos": p.get("photos", []),
            }
            for p in products
        ],
    }
    (outdir / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False))


def main() -> None:
    src, dest = Path(sys.argv[1]), Path(sys.argv[2])
    data = json.loads(src.read_text())
    build(data["company"], data["categories"], data["products"], dest)
    print(f"ok: {dest} に生成した")


if __name__ == "__main__":
    main()
