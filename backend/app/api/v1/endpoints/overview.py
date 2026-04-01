# this file serves dashboard overview data
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import OverviewResponse
from app.services.analysis.metrics import get_overview_payload

router = APIRouter()


@router.get("", response_model=OverviewResponse)
def get_overview(db: Session = Depends(get_db)) -> dict:
    # this endpoint returns top line overview cards and trends
    return get_overview_payload(db)
