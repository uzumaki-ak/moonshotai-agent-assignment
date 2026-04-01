# this file serves review list with filters
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Product, Review
from app.schemas.review import ReviewRead

router = APIRouter()


@router.get("", response_model=list[ReviewRead])
def list_reviews(
    product_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    sentiment: Optional[str] = Query(default=None, pattern="^(positive|negative|neutral)$"),
    rating_min: Optional[float] = None,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    # this endpoint returns filtered review rows for debug and drilldown
    query = select(Review).join(Product, Product.id == Review.product_id)

    filters = []
    if product_id is not None:
        filters.append(Review.product_id == product_id)
    if brand_id is not None:
        filters.append(Product.brand_id == brand_id)
    if sentiment is not None:
        filters.append(Review.sentiment_label == sentiment)
    if rating_min is not None:
        filters.append(Review.rating >= rating_min)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(Review.created_at.desc()).offset(offset).limit(limit)
    rows = db.execute(query).scalars().all()
    payload = []
    for row in rows:
        item = {
            "id": row.id,
            "product_id": row.product_id,
            "rating": row.rating,
            "sentiment_score": row.sentiment_score,
            "sentiment_label": row.sentiment_label,
            "title": row.title,
            "content": row.content,
            "review_date": row.review_date,
            "verified_purchase": row.verified_purchase,
            "helpful_votes": row.helpful_votes,
            "source_url": (row.raw_payload or {}).get("source_url") if isinstance(row.raw_payload, dict) else None,
        }
        payload.append(item)
    return payload
