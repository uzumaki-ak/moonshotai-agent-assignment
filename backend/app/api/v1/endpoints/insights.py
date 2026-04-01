# this file serves generated agent insights
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Insight
from app.schemas.insight import InsightRead

router = APIRouter()


@router.get("/agent", response_model=list[InsightRead])
def get_agent_insights(db: Session = Depends(get_db)) -> list[Insight]:
    # this endpoint returns latest insight cards for dashboard
    return db.execute(select(Insight).order_by(Insight.created_at.desc())).scalars().all()
