# this file runs scrape and analysis jobs end to end
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from slugify import slugify
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Brand, PipelineJob, Product, Review, Theme
from app.services.analysis.metrics import get_brand_comparison, upsert_daily_brand_metrics
from app.services.analysis.sentiment import compute_review_sentiment
from app.services.analysis.themes import extract_themes
from app.services.insights.agent_insights import generate_and_store_insights
from app.services.scraper.amazon_scraper import AmazonScraper

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "cleaned"

RAW_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    # this function returns current utc time string for file naming
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _parse_date(value: Optional[str]) -> Optional[date]:
    # this helper converts iso date strings safely
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except Exception:
        return None


def _update_job(job_id: str, **kwargs) -> None:
    # this helper updates job status fields in db
    with SessionLocal() as db:
        job = db.get(PipelineJob, job_id)
        if not job:
            return
        for key, value in kwargs.items():
            setattr(job, key, value)
        db.commit()


def run_scrape_job(job_id: str) -> None:
    # this function runs async scraper in a sync background task wrapper
    asyncio.run(_run_scrape_job_async(job_id))


async def _run_scrape_job_async(job_id: str) -> None:
    # this function executes scraping for selected brands
    _update_job(job_id, status="running")

    with SessionLocal() as db:
        job = db.get(PipelineJob, job_id)
        if not job:
            return
        params = job.params or {}

    brands = params.get("brands", [])
    products_per_brand = int(params.get("products_per_brand", 10))
    reviews_per_product = int(params.get("reviews_per_product", 50))

    scraper = AmazonScraper()
    total_products = 0
    total_reviews = 0

    try:
        for brand_name in brands:
            payload = await scraper.scrape_brand(
                brand_name=brand_name,
                products_limit=products_per_brand,
                reviews_limit=reviews_per_product,
            )

            # this stores raw scrape output for audit and reproducibility
            raw_path = RAW_DIR / f"{slugify(brand_name)}_{_now_iso()}.json"
            raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            with SessionLocal() as db:
                saved_products, saved_reviews = _persist_brand_payload(db, brand_name, payload)
                total_products += saved_products
                total_reviews += saved_reviews

        _update_job(
            job_id,
            status="completed",
            result={
                "brands": brands,
                "products_saved": total_products,
                "reviews_saved": total_reviews,
            },
            completed_at=datetime.utcnow(),
        )
    except Exception as exc:
        logger.exception("scrape job failed")
        _update_job(
            job_id,
            status="failed",
            error_message=str(exc),
            completed_at=datetime.utcnow(),
        )


def _persist_brand_payload(db, brand_name: str, payload: dict) -> tuple[int, int]:
    # this function upserts one brand payload into normalized tables
    brand = db.execute(select(Brand).where(Brand.name == brand_name)).scalar_one_or_none()
    if not brand:
        brand = Brand(name=brand_name, slug=slugify(brand_name))
        db.add(brand)
        db.flush()

    saved_products = 0
    saved_reviews = 0

    for product_data in payload.get("products", []):
        asin = product_data.get("asin")
        title = product_data.get("title")
        if not asin or not title:
            continue

        product = db.execute(select(Product).where(Product.asin == asin)).scalar_one_or_none()
        if not product:
            product = Product(brand_id=brand.id, asin=asin, title=title, url=product_data.get("url") or "")
            db.add(product)
            db.flush()

        product.brand_id = brand.id
        product.title = title
        product.url = product_data.get("url") or product.url
        product.category = product_data.get("category")
        product.size = product_data.get("size")
        product.price = product_data.get("price")
        product.list_price = product_data.get("list_price")
        product.discount_percent = product_data.get("discount_percent")
        product.rating = product_data.get("rating")
        product.review_count = product_data.get("review_count")
        product.last_scraped_at = datetime.utcnow()

        # this delete and insert step avoids stale review duplicates across reruns
        db.query(Review).filter(Review.product_id == product.id).delete(synchronize_session=False)

        for review_data in product_data.get("reviews", []):
            content = (review_data.get("content") or "").strip()
            if not content:
                continue
            review = Review(
                product_id=product.id,
                review_id=review_data.get("review_id"),
                title=review_data.get("title"),
                content=content,
                rating=review_data.get("rating"),
                review_date=_parse_date(review_data.get("review_date")),
                verified_purchase=review_data.get("verified_purchase"),
                helpful_votes=review_data.get("helpful_votes"),
                raw_payload=review_data.get("raw_payload"),
            )
            db.add(review)
            saved_reviews += 1

        saved_products += 1

    db.commit()
    return saved_products, saved_reviews


def run_analyze_job(job_id: str) -> None:
    # this function runs analysis and insight generation
    asyncio.run(_run_analyze_job_async(job_id))


async def _run_analyze_job_async(job_id: str) -> None:
    # this function processes sentiment themes and insights
    _update_job(job_id, status="running")

    try:
        with SessionLocal() as db:
            _compute_review_sentiments(db)
            _rebuild_themes(db)
            metrics_count = upsert_daily_brand_metrics(db)
            insight_count = await generate_and_store_insights(db)
            _export_clean_datasets(db)

        _update_job(
            job_id,
            status="completed",
            result={
                "metrics_rows": metrics_count,
                "insights_created": insight_count,
                "dataset_path": str(CLEAN_DIR),
            },
            completed_at=datetime.utcnow(),
        )
    except Exception as exc:
        logger.exception("analysis job failed")
        _update_job(
            job_id,
            status="failed",
            error_message=str(exc),
            completed_at=datetime.utcnow(),
        )


def _compute_review_sentiments(db) -> None:
    # this function computes sentiment fields for every review
    reviews = db.execute(select(Review)).scalars().all()
    for review in reviews:
        result = compute_review_sentiment(review.content, review.rating)
        review.sentiment_score = result.score
        review.sentiment_label = result.label
    db.commit()


def _rebuild_themes(db) -> None:
    # this function refreshes theme tables for brands and products
    db.query(Theme).delete(synchronize_session=False)

    products = db.execute(select(Product)).scalars().all()
    for product in products:
        review_rows = db.execute(select(Review).where(Review.product_id == product.id)).scalars().all()
        review_payload = [
            {
                "content": row.content,
                "sentiment_score": row.sentiment_score,
            }
            for row in review_rows
        ]
        grouped = extract_themes(review_payload)

        for theme_type, hits in grouped.items():
            for hit in hits[:5]:
                db.add(
                    Theme(
                        brand_id=product.brand_id,
                        product_id=product.id,
                        theme_type=theme_type,
                        aspect=hit.aspect,
                        mention_count=hit.mention_count,
                        avg_sentiment=hit.avg_sentiment,
                        sample_quotes=hit.sample_quotes,
                    )
                )

    db.commit()


def _export_clean_datasets(db) -> None:
    # this function writes cleaned csv files used by dashboard and review
    products = db.execute(
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
            Product.last_scraped_at,
        ).join(Brand, Brand.id == Product.brand_id)
    ).all()

    reviews = db.execute(
        select(
            Review.id,
            Review.product_id,
            Product.brand_id,
            Brand.name.label("brand_name"),
            Product.asin,
            Review.rating,
            Review.sentiment_score,
            Review.sentiment_label,
            Review.title,
            Review.content,
            Review.review_date,
            Review.verified_purchase,
            Review.helpful_votes,
        )
        .join(Product, Product.id == Review.product_id)
        .join(Brand, Brand.id == Product.brand_id)
    ).all()

    themes = db.execute(
        select(
            Theme.id,
            Theme.brand_id,
            Brand.name.label("brand_name"),
            Theme.product_id,
            Theme.theme_type,
            Theme.aspect,
            Theme.mention_count,
            Theme.avg_sentiment,
            Theme.sample_quotes,
        )
        .join(Brand, Brand.id == Theme.brand_id, isouter=True)
    ).all()

    comparison = get_brand_comparison(db)

    pd.DataFrame([row._asdict() for row in products]).to_csv(CLEAN_DIR / "products_clean.csv", index=False)
    pd.DataFrame([row._asdict() for row in reviews]).to_csv(CLEAN_DIR / "reviews_clean.csv", index=False)
    pd.DataFrame([row._asdict() for row in themes]).to_csv(CLEAN_DIR / "themes_clean.csv", index=False)
    pd.DataFrame(comparison).to_csv(CLEAN_DIR / "brand_comparison_clean.csv", index=False)
