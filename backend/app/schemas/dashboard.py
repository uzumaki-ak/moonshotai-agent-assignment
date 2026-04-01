# this file defines dashboard overview schemas
from typing import Optional

from pydantic import BaseModel


class OverviewStats(BaseModel):
    # this schema is used for top summary cards
    total_brands: int
    total_products: int
    total_reviews: int
    avg_sentiment: Optional[float] = None
    avg_price: Optional[float] = None


class PriceBandDistribution(BaseModel):
    # this schema returns premium vs value split
    band: str
    product_count: int


class SentimentTrendPoint(BaseModel):
    # this schema returns trend points by date
    date: str
    sentiment: float


class OverviewResponse(BaseModel):
    # this schema returns dashboard overview payload
    stats: OverviewStats
    price_bands: list[PriceBandDistribution]
    sentiment_trend: list[SentimentTrendPoint]
