from typing import Literal

from pydantic import BaseModel, Field


class CartItemIn(BaseModel):
    quantity: int = Field(ge=1)
    spec_note: str | None = None  # 個別仕様(色・寸法指定等)


class CartItemOut(BaseModel):
    code: str
    name: str
    quantity: int
    spec_note: str | None
    price_note: str | None
    photo: str | None


class QuoteCreateIn(BaseModel):
    note: str | None = None  # 依頼時の要望


class QuoteItemOut(BaseModel):
    code: str
    name: str
    quantity: int
    spec_note: str | None


class QuoteListItem(BaseModel):
    id: str
    quote_no: str
    status: str
    created_at: str
    last_message: str | None
    last_message_at: str | None


class QuoteDetail(BaseModel):
    id: str
    quote_no: str
    status: str
    note: str | None
    created_at: str
    answered_at: str | None
    ordered_at: str | None
    items: list[QuoteItemOut]


class QuotePatchIn(BaseModel):
    # 顧客が変えられるのはこの2つだけ(02_api)
    status: Literal["cancelled", "ordered"]


class MessageOut(BaseModel):
    id: str
    body: str
    has_file: bool
    sent_at: str
    read_at: str | None
    is_mine: bool


class MessageCreated(BaseModel):
    id: str
