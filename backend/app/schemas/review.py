# this file defines review schemas
from datetime import date
from typing import Optional

from pydantic import BaseModel


class ReviewRead(BaseModel):
    # this schema sends review level data to ui
    id: int
    product_id: int
    rating: Optional[float] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    title: Optional[str] = None
    content: str
    review_date: Optional[date] = None
    verified_purchase: Optional[bool] = None
    helpful_votes: Optional[int] = None
    source_url: Optional[str] = None
