from typing import Any

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    sort_order: int


class ProductCard(BaseModel):
    """一覧用。カード表示の並び: 写真/一言/型番/仕様抜粋/価格表記(03_apps)"""

    code: str
    name: str
    summary: str | None
    specs: dict[str, Any]
    price_note: str | None
    photo: str | None  # 先頭の写真パス
    category_slug: str


class ProductDetail(BaseModel):
    code: str
    name: str
    summary: str | None
    description: str | None
    specs: dict[str, Any]
    price_note: str | None
    photos: list[str]
    category_slug: str
    category_name: str
