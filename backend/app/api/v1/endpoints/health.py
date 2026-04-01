# this file exposes health endpoint
from datetime import datetime

from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    # this endpoint returns service health for smoke checks
    return HealthResponse(status="ok", timestamp=datetime.utcnow())
