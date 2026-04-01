# this file defines pipeline job schemas
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScrapeJobCreate(BaseModel):
    # this schema starts a scrape job
    brands: list[str]
    products_per_brand: int = 10
    reviews_per_product: int = 50


class AnalyzeJobCreate(BaseModel):
    # this schema starts analysis job
    force_recompute: bool = False
    source_scrape_job_id: Optional[str] = None


class JobRead(BaseModel):
    # this schema returns job state
    id: str
    job_type: str
    status: str
    params: Optional[dict] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
