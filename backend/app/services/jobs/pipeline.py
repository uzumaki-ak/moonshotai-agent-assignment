# this file runs scrape and analysis jobs end to end
from __future__ import annotations

import asyncio
import csv
import json
import logging
import sys
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
RUNS_DIR = PROJECT_ROOT / "data" / "runs"

RAW_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)


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


def _ensure_error_message(exc: Exception) -> str:
    # this helper avoids empty error strings in job table
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__


def _run_path(job_id: str, section: str) -> Path:
    # this helper returns consistent run scoped folder paths
    path = RUNS_DIR / job_id / section
    path.mkdir(parents=True, exist_ok=True)
    return path


def _latest_completed_scrape_job_id() -> Optional[str]:
    # this helper fetches most recent completed scrape job
    with SessionLocal() as db:
        row = (
            db.query(PipelineJob)
            .filter(PipelineJob.job_type == "scrape", PipelineJob.status == "completed")
            .order_by(PipelineJob.completed_at.desc().nullslast(), PipelineJob.started_at.desc())
            .first()
        )
        return row.id if row else None


def _get_scrape_run_files(scrape_job_id: str, allow_legacy_fallback: bool = False) -> list[Path]:
    # this helper resolves raw json files for one scrape run
    run_raw_dir = _run_path(scrape_job_id, "raw")
    files = sorted(run_raw_dir.glob("*.json"))
    if files:
        return files

    if allow_legacy_fallback:
        # this fallback supports legacy raw storage before run folders were added
        legacy = sorted(RAW_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        return legacy
    return []


def _reset_operational_tables(db) -> None:
    # this helper clears derived tables before rebuilding from a selected run
    db.query(Review).delete(synchronize_session=False)
    db.query(Theme).delete(synchronize_session=False)
    db.query(Product).delete(synchronize_session=False)
    db.commit()


def _hydrate_db_from_scrape_run(scrape_job_id: str, allow_legacy_fallback: bool = False) -> dict:
    # this helper loads selected scrape run raw json into normalized tables
    raw_files = _get_scrape_run_files(scrape_job_id, allow_legacy_fallback=allow_legacy_fallback)
    if not raw_files:
        raise RuntimeError(f"no raw artifacts found for scrape run {scrape_job_id}")
    loaded_products = 0
    loaded_reviews = 0
    loaded_brands: list[str] = []

    with SessionLocal() as db:
        _reset_operational_tables(db)

        for raw_file in raw_files:
            payload = json.loads(raw_file.read_text(encoding="utf-8"))
            brand_name = payload.get("brand")
            if not brand_name:
                continue
            saved_products, saved_reviews = _persist_brand_payload(db, brand_name, payload)
            loaded_products += saved_products
            loaded_reviews += saved_reviews
            loaded_brands.append(brand_name)

    return {
        "source_scrape_job_id": scrape_job_id,
        "raw_files": [str(path) for path in raw_files],
        "brands": sorted(list(set(loaded_brands))),
        "products_loaded": loaded_products,
        "reviews_loaded": loaded_reviews,
    }


def _run_async_job(coro) -> None:
    # this helper ensures windows jobs use subprocess friendly event loop
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())  # type: ignore[attr-defined]
        except Exception:
            pass
    asyncio.run(coro)


def run_scrape_job(job_id: str) -> None:
    # this function runs async scraper in a sync background task wrapper
    _run_async_job(_run_scrape_job_async(job_id))


async def run_scrape_job_async(job_id: str) -> None:
    # this function runs scrape job directly on current event loop
    await _run_scrape_job_async(job_id)


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
    run_raw_dir = _run_path(job_id, "raw")
    file_manifest: list[dict] = []
    warnings: list[str] = []

    try:
        for brand_name in brands:
            payload = await scraper.scrape_brand(
                brand_name=brand_name,
                products_limit=products_per_brand,
                reviews_limit=reviews_per_product,
            )

            # this stores raw scrape output for audit and reproducibility
            raw_path = run_raw_dir / f"{slugify(brand_name)}_{_now_iso()}.json"
            raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            # this keeps latest raw snapshots for quick access
            (RAW_DIR / raw_path.name).write_text(json.dumps(payload, indent=2), encoding="utf-8")

            with SessionLocal() as db:
                saved_products, saved_reviews = _persist_brand_payload(db, brand_name, payload)
                total_products += saved_products
                total_reviews += saved_reviews
                file_manifest.append(
                    {
                        "brand": brand_name,
                        "path": str(raw_path),
                        "products_saved": saved_products,
                        "reviews_saved": saved_reviews,
                    }
                )

            payload_warnings = payload.get("warnings", [])
            if payload_warnings:
                warnings.extend(payload_warnings)
            if saved_reviews == 0:
                warnings.append(
                    f"{brand_name} scrape saved products but no reviews. this can happen when amazon review pages are blocked."
                )

        _update_job(
            job_id,
            status="completed",
            result={
                "brands": brands,
                "products_saved": total_products,
                "reviews_saved": total_reviews,
                "run_id": job_id,
                "artifacts": {
                    "raw_dir": str(run_raw_dir),
                    "files": file_manifest,
                    "warnings": warnings,
                },
            },
            completed_at=datetime.utcnow(),
        )
    except Exception as exc:
        logger.exception("scrape job failed")
        _update_job(
            job_id,
            status="failed",
            error_message=_ensure_error_message(exc),
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
            raw_payload = review_data.get("raw_payload") or {}
            if "source_url" not in raw_payload:
                raw_payload["source_url"] = f"https://www.amazon.in/product-reviews/{asin}"
            if "product_url" not in raw_payload:
                raw_payload["product_url"] = product_data.get("url")
            review = Review(
                product_id=product.id,
                review_id=review_data.get("review_id"),
                title=review_data.get("title"),
                content=content,
                rating=review_data.get("rating"),
                review_date=_parse_date(review_data.get("review_date")),
                verified_purchase=review_data.get("verified_purchase"),
                helpful_votes=review_data.get("helpful_votes"),
                raw_payload=raw_payload,
            )
            db.add(review)
            saved_reviews += 1

        saved_products += 1

    db.commit()
    return saved_products, saved_reviews


def run_analyze_job(job_id: str) -> None:
    # this function runs analysis and insight generation
    _run_async_job(_run_analyze_job_async(job_id))


async def run_analyze_job_async(job_id: str) -> None:
    # this function runs analyze job directly on current event loop
    await _run_analyze_job_async(job_id)


async def _run_analyze_job_async(job_id: str) -> None:
    # this function processes sentiment themes and insights
    _update_job(job_id, status="running")

    try:
        with SessionLocal() as db:
            analyze_job = db.get(PipelineJob, job_id)
            params = analyze_job.params if analyze_job else {}

        source_scrape_job_id = params.get("source_scrape_job_id") if params else None
        explicit_source = bool(source_scrape_job_id)
        if not source_scrape_job_id:
            source_scrape_job_id = _latest_completed_scrape_job_id()
        if not source_scrape_job_id:
            raise RuntimeError("no completed scrape job available to analyze")

        hydrate_summary = _hydrate_db_from_scrape_run(
            source_scrape_job_id,
            allow_legacy_fallback=not explicit_source,
        )

        cleaned_dir = _run_path(job_id, "cleaned")
        with SessionLocal() as db:
            _compute_review_sentiments(db)
            _rebuild_themes(db)
            metrics_count = upsert_daily_brand_metrics(db)
            insight_count = await generate_and_store_insights(db)
            dataset_summary = _export_clean_datasets(db, cleaned_dir=cleaned_dir)

        _update_job(
            job_id,
            status="completed",
            result={
                "source_scrape_job_id": source_scrape_job_id,
                "hydrate_summary": hydrate_summary,
                "metrics_rows": metrics_count,
                "insights_created": insight_count,
                "dataset_path": str(cleaned_dir),
                "artifacts": dataset_summary,
            },
            completed_at=datetime.utcnow(),
        )
    except Exception as exc:
        logger.exception("analysis job failed")
        _update_job(
            job_id,
            status="failed",
            error_message=_ensure_error_message(exc),
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


def _export_clean_datasets(db, cleaned_dir: Path) -> dict:
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
            Review.raw_payload,
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

    products_df = pd.DataFrame([row._asdict() for row in products])
    reviews_rows = []
    for row in reviews:
        item = row._asdict()
        payload = item.pop("raw_payload", None)
        if isinstance(payload, dict):
            item["source_url"] = payload.get("source_url")
            item["reviews_page_url"] = payload.get("reviews_page_url")
        else:
            item["source_url"] = None
            item["reviews_page_url"] = None
        reviews_rows.append(item)
    reviews_df = pd.DataFrame(reviews_rows)
    themes_df = pd.DataFrame([row._asdict() for row in themes])
    comparison_df = pd.DataFrame(comparison)

    # this section writes run scoped files and also refreshes latest snapshot paths
    products_run_path = cleaned_dir / "products_clean.csv"
    reviews_run_path = cleaned_dir / "reviews_clean.csv"
    themes_run_path = cleaned_dir / "themes_clean.csv"
    comparison_run_path = cleaned_dir / "brand_comparison_clean.csv"

    products_df.to_csv(products_run_path, index=False)
    reviews_df.to_csv(reviews_run_path, index=False)
    themes_df.to_csv(themes_run_path, index=False)
    comparison_df.to_csv(comparison_run_path, index=False)

    products_df.to_csv(CLEAN_DIR / "products_clean.csv", index=False)
    reviews_df.to_csv(CLEAN_DIR / "reviews_clean.csv", index=False)
    themes_df.to_csv(CLEAN_DIR / "themes_clean.csv", index=False)
    comparison_df.to_csv(CLEAN_DIR / "brand_comparison_clean.csv", index=False)

    return {
        "cleaned_dir": str(cleaned_dir),
        "files": [
            {"key": "products_clean", "path": str(products_run_path)},
            {"key": "reviews_clean", "path": str(reviews_run_path)},
            {"key": "themes_clean", "path": str(themes_run_path)},
            {"key": "brand_comparison_clean", "path": str(comparison_run_path)},
        ],
        "row_counts": {
            "products": int(len(products_df)),
            "reviews": int(len(reviews_df)),
            "themes": int(len(themes_df)),
            "brand_comparison": int(len(comparison_df)),
        },
    }


def get_job_artifacts(job_id: str) -> dict:
    # this function returns artifact metadata for one completed job
    with SessionLocal() as db:
        job = db.get(PipelineJob, job_id)
        if not job:
            raise RuntimeError("job not found")
        result = job.result or {}

    artifacts = result.get("artifacts") if isinstance(result, dict) else None
    if not artifacts:
        return {"job_id": job_id, "artifacts": {}, "message": "no artifacts found for this job"}
    return {"job_id": job_id, "artifacts": artifacts}


def preview_job_artifact(job_id: str, artifact_key: str, limit: int = 25) -> dict:
    # this function loads preview rows from artifact files for ui verification
    payload = get_job_artifacts(job_id)
    artifacts = payload.get("artifacts", {})
    files = artifacts.get("files", [])
    selected = None

    for row in files:
        key = row.get("key") or row.get("brand")
        if str(key) == artifact_key:
            selected = row
            break

    if not selected:
        raise RuntimeError("artifact not found")

    path = Path(selected["path"]).resolve()
    data_root = (PROJECT_ROOT / "data").resolve()
    if data_root not in path.parents and path != data_root:
        raise RuntimeError("artifact path is outside data directory")
    if not path.exists():
        raise RuntimeError("artifact file not found on disk")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        products = data.get("products", []) if isinstance(data, dict) else []
        preview = []
        for row in products[:limit]:
            preview.append(
                {
                    "asin": row.get("asin"),
                    "title": row.get("title"),
                    "price": row.get("price"),
                    "rating": row.get("rating"),
                    "review_count": row.get("review_count"),
                    "product_url": row.get("url"),
                    "reviews_scraped": len(row.get("reviews", [])),
                    "reviews_page": f"https://www.amazon.in/product-reviews/{row.get('asin')}" if row.get("asin") else None,
                }
            )

        if not preview:
            for row in (data.get("attempted_search_urls", []) if isinstance(data, dict) else [])[:limit]:
                preview.append(
                    {
                        "search_url": row.get("search_url"),
                        "page_title": row.get("page_title"),
                        "blocked": row.get("blocked"),
                        "no_results": row.get("no_results"),
                    }
                )
        return {
            "job_id": job_id,
            "artifact_key": artifact_key,
            "path": str(path),
            "rows": preview,
            "row_count": len(preview),
        }

    if path.suffix.lower() == ".csv":
        rows = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader):
                if index >= limit:
                    break
                rows.append(row)
        return {
            "job_id": job_id,
            "artifact_key": artifact_key,
            "path": str(path),
            "rows": rows,
            "row_count": len(rows),
        }

    raise RuntimeError("unsupported artifact file type")
