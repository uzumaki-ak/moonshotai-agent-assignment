# this file defines schemas for brand APIs
from typing import Optional

from pydantic import BaseModel, Field


class BrandBase(BaseModel):
    # this schema carries basic brand fields
    name: str = Field(..., min_length=2)


class BrandCreate(BrandBase):
    # this schema is used when creating a brand
    pass


class BrandRead(BrandBase):
    # this schema is used in list responses
    id: int
    slug: str

    class Config:
        from_attributes = True


class BrandComparisonRow(BaseModel):
    # this schema holds brand comparison metrics
    brand_id: int
    brand_name: str
    avg_price: Optional[float] = None
    avg_discount_pct: Optional[float] = None
    avg_rating: Optional[float] = None
    review_count: int = 0
    sentiment_score: Optional[float] = None
    premium_index: Optional[float] = None
    value_for_money: Optional[float] = None
    top_praise: list[str] = []
    top_complaints: list[str] = []


class BrandDetail(BrandRead):
    # this schema is used on brand detail page
    product_count: int
    review_count: int
    avg_price: Optional[float] = None
    avg_discount_pct: Optional[float] = None
    avg_rating: Optional[float] = None
    sentiment_score: Optional[float] = None
