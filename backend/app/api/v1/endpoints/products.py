# this file serves product list and drilldown routes
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Brand, Product, Review, Theme
from app.schemas.product import ProductDetail, ProductRead

router = APIRouter()


@router.get("", response_model=list[ProductRead])
def list_products(
    brand_id: Optional[int] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    rating_min: Optional[float] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    # this endpoint returns filtered products for grid and table views
    query = (
        select(
            Product.id,
            Product.brand_id,
            Brand.name.label("brand_name"),
            Product.asin,
            Product.title,
            Product.url,
            Product.category,
            Product.size,
            Product.price,
            Product.list_price,
            Product.discount_percent,
            Product.rating,
            Product.review_count,
        )
        .join(Brand, Brand.id == Product.brand_id)
        .order_by(Product.review_count.desc().nullslast())
    )

    filters = []
    if brand_id:
        filters.append(Product.brand_id == brand_id)
    if price_min is not None:
        filters.append(Product.price >= price_min)
    if price_max is not None:
        filters.append(Product.price <= price_max)
    if rating_min is not None:
        filters.append(Product.rating >= rating_min)

    if filters:
        query = query.where(and_(*filters))

    rows = db.execute(query.limit(limit).offset(offset)).all()
    return [row._asdict() for row in rows]


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db)) -> dict:
    # this endpoint returns full product drilldown data
    row = db.execute(
        select(
            Product.id,
            Product.brand_id,
            Brand.name.label("brand_name"),
            Product.asin,
            Product.title,
            Product.url,
            Product.category,
            Product.size,
            Product.price,
            Product.list_price,
            Product.discount_percent,
            Product.rating,
            Product.review_count,
            func.avg(Review.sentiment_score).label("sentiment_score"),
        )
        .join(Brand, Brand.id == Product.brand_id)
        .join(Review, Review.product_id == Product.id, isouter=True)
        .where(Product.id == product_id)
        .group_by(
            Product.id,
            Product.brand_id,
            Brand.name,
            Product.asin,
            Product.title,
            Product.url,
            Product.category,
            Product.size,
            Product.price,
            Product.list_price,
            Product.discount_percent,
            Product.rating,
            Product.review_count,
        )
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="product not found")

    praise_rows = db.execute(
        select(Theme.aspect)
        .where(Theme.product_id == product_id, Theme.theme_type == "praise")
        .order_by(Theme.mention_count.desc())
        .limit(4)
    ).all()
    complaint_rows = db.execute(
        select(Theme.aspect)
        .where(Theme.product_id == product_id, Theme.theme_type == "complaint")
        .order_by(Theme.mention_count.desc())
        .limit(4)
    ).all()

    top_praise = [item.aspect for item in praise_rows]
    top_complaints = [item.aspect for item in complaint_rows]

    # this small synthesis is kept deterministic for stable output
    synthesis_bits = []
    if top_praise:
        synthesis_bits.append(f"customers praise {', '.join(top_praise)}")
    if top_complaints:
        synthesis_bits.append(f"common complaints mention {', '.join(top_complaints)}")

    payload = row._asdict()
    payload["top_praise"] = top_praise
    payload["top_complaints"] = top_complaints
    payload["review_synthesis"] = ". ".join(synthesis_bits) if synthesis_bits else "insufficient review text for synthesis"

    return payload
