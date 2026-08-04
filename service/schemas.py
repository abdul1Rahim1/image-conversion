from typing import Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool
    catalog_size: int
    cached: int


class SearchHit(BaseModel):
    asin: str
    title: str
    price: float | None
    currency: str | None
    source_image_url: str | None
    status: str


class SearchResponse(BaseModel):
    query: str
    count: int
    hits: list[SearchHit]


class ProductResponse(BaseModel):
    asin: str
    status: str
    product: dict[str, Any] | None = None
