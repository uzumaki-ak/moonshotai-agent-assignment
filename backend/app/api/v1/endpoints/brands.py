# this file serves brand level routes
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Brand
from app.schemas.brand import BrandComparisonRow, BrandDetail, BrandRead
from app.services.analysis.metrics import get_brand_comparison, get_brand_detail

router = APIRouter()


@router.get("", response_model=list[BrandRead])
def list_brands(db: Session = Depends(get_db)) -> list[Brand]:
    # this endpoint lists all tracked brands
    return db.execute(select(Brand).order_by(Brand.name.asc())).scalars().all()


@router.get("/compare", response_model=list[BrandComparisonRow])
def compare_brands(
    brand_ids: list[int] = Query(default=[]),
    db: Session = Depends(get_db),
) -> list[dict]:
    # this endpoint returns side by side benchmark metrics
    ids = brand_ids if brand_ids else None
    return get_brand_comparison(db, ids)


@router.get("/{brand_id}", response_model=BrandDetail)
def brand_detail(brand_id: int, db: Session = Depends(get_db)) -> dict:
    # this endpoint returns one brand summary for detail page
    payload = get_brand_detail(db, brand_id)
    if not payload:
        raise HTTPException(status_code=404, detail="brand not found")
    return payload
