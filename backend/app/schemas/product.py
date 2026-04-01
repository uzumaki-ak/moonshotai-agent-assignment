# this file defines product schemas for endpoints
from typing import Optional

from pydantic import BaseModel


class ProductRead(BaseModel):
    # this schema carries product data for list view
    id: int
    brand_id: int
    brand_name: str
    asin: str
    title: str
    url: str
    category: Optional[str] = None
    size: Optional[str] = None
    price: Optional[float] = None
    list_price: Optional[float] = None
    discount_percent: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None


class ProductDetail(ProductRead):
    # this schema carries product data for drilldown page
    sentiment_score: Optional[float] = None
    top_praise: list[str] = []
    top_complaints: list[str] = []
    review_synthesis: str = ""
