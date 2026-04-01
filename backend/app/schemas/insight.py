# this file defines insight schemas
from typing import Optional

from pydantic import BaseModel


class InsightRead(BaseModel):
    # this schema sends generated insight cards
    id: int
    insight_type: str
    title: str
    body: str
    confidence: Optional[float] = None
    payload: Optional[dict] = None

    class Config:
        from_attributes = True
