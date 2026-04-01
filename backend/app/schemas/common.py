# this file keeps shared pydantic schema helpers
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    # this schema is used by health endpoint
    status: str
    timestamp: datetime


class MessageResponse(BaseModel):
    # this schema returns plain messages
    message: str


class ErrorResponse(BaseModel):
    # this schema returns user safe errors
    detail: str


class PaginationMeta(BaseModel):
    # this schema carries pagination metadata
    page: int
    page_size: int
    total: int


class PaginatedResponse(BaseModel):
    # this schema wraps list responses with metadata
    meta: PaginationMeta
    data: list[Any]


class DateRangeFilter(BaseModel):
    # this schema supports filtering by snapshot window
    start_date: Optional[str] = None
    end_date: Optional[str] = None
