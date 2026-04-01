# this file computes dashboard metrics from db data
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models import Brand, BrandMetric, Product, Review, Theme


def _to_float(value) -> Optional[float]:
    # this helper safely converts decimal values to float
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def get_overview_payload(db: Session) -> dict:
    # this function builds overview cards and trend data
    total_brands = db.scalar(select(func.count(func.distinct(Product.brand_id)))) or 0
    total_products = db.scalar(select(func.count(Product.id))) or 0
    total_reviews = db.scalar(select(func.count(Review.id))) or 0

    avg_sentiment = db.scalar(select(func.avg(Review.sentiment_score)))
    avg_price = db.scalar(select(func.avg(Product.price)))

    band_query = (
        select(
            func.sum(case((Product.price < 1500, 1), else_=0)).label("budget"),
            func.sum(case((and_(Product.price >= 1500, Product.price < 3000), 1), else_=0)).label("mid"),
            func.sum(case((Product.price >= 3000, 1), else_=0)).label("premium"),
        )
        .where(Product.price.is_not(None))
    )
    band_row = db.execute(band_query).one()

    trend_rows = db.execute(
        select(
            func.date(Review.created_at).label("created_day"),
            func.avg(Review.sentiment_score).label("sentiment"),
        )
        .where(Review.sentiment_score.is_not(None))
        .group_by(func.date(Review.created_at))
        .order_by(func.date(Review.created_at).asc())
        .limit(30)
    ).all()

    trend = [
        {
            "date": str(row.created_day),
            "sentiment": round(float(row.sentiment or 0.0), 4),
        }
        for row in trend_rows
    ]

    return {
        "stats": {
            "total_brands": total_brands,
            "total_products": total_products,
            "total_reviews": total_reviews,
            "avg_sentiment": round(float(avg_sentiment or 0.0), 4) if avg_sentiment is not None else None,
            "avg_price": round(float(avg_price or 0.0), 2) if avg_price is not None else None,
        },
        "price_bands": [
            {"band": "value", "product_count": int(band_row.budget or 0)},
            {"band": "mid", "product_count": int(band_row.mid or 0)},
            {"band": "premium", "product_count": int(band_row.premium or 0)},
        ],
        "sentiment_trend": trend,
    }


def _top_theme_names(db: Session, brand_id: int, theme_type: str, limit: int = 3) -> list[str]:
    # this helper fetches top theme names for one brand
    rows = db.execute(
        select(Theme.aspect)
        .where(Theme.brand_id == brand_id, Theme.theme_type == theme_type)
        .order_by(Theme.mention_count.desc())
        .limit(limit)
    ).all()
    return [row.aspect for row in rows]


def get_brand_comparison(db: Session, brand_ids: Optional[list[int]] = None) -> list[dict]:
    # this function returns side by side brand metrics
    product_stats = (
        select(
            Product.brand_id.label("brand_id"),
            func.count(Product.id).label("product_count"),
            func.avg(Product.price).label("avg_price"),
            func.avg(Product.discount_percent).label("avg_discount_pct"),
            func.avg(Product.rating).label("avg_rating"),
            func.coalesce(func.sum(Product.review_count), 0).label("review_count"),
        )
        .group_by(Product.brand_id)
        .subquery()
    )

    review_stats = (
        select(
            Product.brand_id.label("brand_id"),
            func.avg(Review.sentiment_score).label("sentiment_score"),
        )
        .select_from(Product)
        .join(Review, Review.product_id == Product.id)
        .group_by(Product.brand_id)
        .subquery()
    )

    query = (
        select(
            Brand.id.label("brand_id"),
            Brand.name.label("brand_name"),
            product_stats.c.avg_price.label("avg_price"),
            product_stats.c.avg_discount_pct.label("avg_discount_pct"),
            product_stats.c.avg_rating.label("avg_rating"),
            product_stats.c.review_count.label("review_count"),
            review_stats.c.sentiment_score.label("sentiment_score"),
        )
        .select_from(Brand)
        .join(product_stats, product_stats.c.brand_id == Brand.id, isouter=True)
        .join(review_stats, review_stats.c.brand_id == Brand.id, isouter=True)
        .order_by(product_stats.c.avg_price.desc().nullslast())
    )

    if brand_ids:
        query = query.where(Brand.id.in_(brand_ids))

    rows = db.execute(query).all()

    active_rows = [row for row in rows if row.avg_price is not None or row.review_count not in (None, 0) or row.avg_rating is not None]

    if not active_rows:
        return []

    avg_market_price = sum(float(row.avg_price or 0.0) for row in active_rows) / max(len(active_rows), 1)

    payload = []
    for row in active_rows:
        avg_price = _to_float(row.avg_price)
        sentiment = _to_float(row.sentiment_score)
        discount = _to_float(row.avg_discount_pct)

        premium_index = None
        value_for_money = None
        if avg_price is not None and avg_market_price > 0:
            premium_index = round(avg_price / avg_market_price, 4)
        if sentiment is not None and avg_price is not None and avg_price > 0:
            value_for_money = round(sentiment * 1000 / avg_price, 4)

        payload.append(
            {
                "brand_id": int(row.brand_id),
                "brand_name": row.brand_name,
                "avg_price": round(avg_price, 2) if avg_price is not None else None,
                "avg_discount_pct": round(discount, 2) if discount is not None else None,
                "avg_rating": round(_to_float(row.avg_rating), 2) if row.avg_rating is not None else None,
                "review_count": int(row.review_count or 0),
                "sentiment_score": round(sentiment, 4) if sentiment is not None else None,
                "premium_index": premium_index,
                "value_for_money": value_for_money,
                "top_praise": _top_theme_names(db, int(row.brand_id), "praise"),
                "top_complaints": _top_theme_names(db, int(row.brand_id), "complaint"),
            }
        )

    return payload


def get_brand_detail(db: Session, brand_id: int) -> Optional[dict]:
    # this function returns one brand detail card
    product_stats = (
        select(
            Product.brand_id.label("brand_id"),
            func.count(Product.id).label("product_count"),
            func.coalesce(func.sum(Product.review_count), 0).label("review_count"),
            func.avg(Product.price).label("avg_price"),
            func.avg(Product.discount_percent).label("avg_discount_pct"),
            func.avg(Product.rating).label("avg_rating"),
        )
        .group_by(Product.brand_id)
        .subquery()
    )

    review_stats = (
        select(
            Product.brand_id.label("brand_id"),
            func.avg(Review.sentiment_score).label("sentiment_score"),
        )
        .select_from(Product)
        .join(Review, Review.product_id == Product.id)
        .group_by(Product.brand_id)
        .subquery()
    )

    row = db.execute(
        select(
            Brand.id,
            Brand.name,
            Brand.slug,
            product_stats.c.product_count.label("product_count"),
            product_stats.c.review_count.label("review_count"),
            product_stats.c.avg_price.label("avg_price"),
            product_stats.c.avg_discount_pct.label("avg_discount_pct"),
            product_stats.c.avg_rating.label("avg_rating"),
            review_stats.c.sentiment_score.label("sentiment_score"),
        )
        .select_from(Brand)
        .join(product_stats, product_stats.c.brand_id == Brand.id, isouter=True)
        .join(review_stats, review_stats.c.brand_id == Brand.id, isouter=True)
        .where(Brand.id == brand_id)
    ).first()

    if not row:
        return None

    if not any([row.product_count, row.review_count, row.avg_price, row.avg_rating, row.sentiment_score]):
        return None

    return {
        "id": int(row.id),
        "name": row.name,
        "slug": row.slug,
        "product_count": int(row.product_count or 0),
        "review_count": int(row.review_count or 0),
        "avg_price": round(_to_float(row.avg_price), 2) if row.avg_price is not None else None,
        "avg_discount_pct": round(_to_float(row.avg_discount_pct), 2) if row.avg_discount_pct is not None else None,
        "avg_rating": round(_to_float(row.avg_rating), 2) if row.avg_rating is not None else None,
        "sentiment_score": round(_to_float(row.sentiment_score), 4) if row.sentiment_score is not None else None,
    }


def upsert_daily_brand_metrics(db: Session, snapshot: Optional[date] = None) -> int:
    # this function stores one daily snapshot for all brands
    snapshot_date = snapshot or date.today()
    comparison = get_brand_comparison(db)

    # this section replaces old snapshot rows to keep one row per brand per date
    brand_ids = [row["brand_id"] for row in comparison]
    if brand_ids:
        db.query(BrandMetric).filter(
            BrandMetric.snapshot_date == snapshot_date,
            BrandMetric.brand_id.in_(brand_ids),
        ).delete(synchronize_session=False)

    count = 0
    for row in comparison:
        metric = BrandMetric(
            brand_id=row["brand_id"],
            snapshot_date=snapshot_date,
            avg_price=row["avg_price"],
            avg_discount_pct=row["avg_discount_pct"],
            avg_rating=row["avg_rating"],
            total_reviews=row["review_count"],
            sentiment_score=row["sentiment_score"],
            premium_index=row["premium_index"],
            value_for_money=row["value_for_money"],
        )
        db.add(metric)
        count += 1

    db.commit()
    return count


def get_price_position_labels(db: Session) -> dict[int, str]:
    # this function labels each brand into value mid premium position
    rows = get_brand_comparison(db)
    prices = [row["avg_price"] for row in rows if row["avg_price"] is not None]
    if not prices:
        return {}

    low = min(prices)
    high = max(prices)
    span = max(high - low, 1)

    labels: dict[int, str] = {}
    for row in rows:
        price = row["avg_price"]
        if price is None:
            labels[row["brand_id"]] = "unknown"
            continue
        rel = (price - low) / span
        if rel < 0.33:
            labels[row["brand_id"]] = "value"
        elif rel < 0.66:
            labels[row["brand_id"]] = "mid"
        else:
            labels[row["brand_id"]] = "premium"
    return labels
