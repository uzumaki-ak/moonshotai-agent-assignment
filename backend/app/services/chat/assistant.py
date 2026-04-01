# this file builds grounded context from the database and answers user questions
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import Brand, Product, Review, Theme
from app.services.analysis.metrics import get_brand_comparison
from app.services.llm.router import LlmRouter


def _safe_float(value) -> Optional[float]:
    # this helper converts db numeric values safely
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _build_context(db: Session, brand_ids: Optional[list[int]] = None) -> dict:
    # this helper gathers grounded dataset context for one chat question
    comparison = get_brand_comparison(db, brand_ids or None)

    product_query = (
        select(
            Brand.name.label("brand_name"),
            Product.title,
            Product.price,
            Product.discount_percent,
            Product.rating,
            Product.review_count,
            Product.url,
        )
        .join(Brand, Brand.id == Product.brand_id)
        .order_by(desc(Product.review_count), desc(Product.rating))
        .limit(10)
    )
    if brand_ids:
        product_query = product_query.where(Product.brand_id.in_(brand_ids))
    product_rows = db.execute(product_query).all()

    theme_query = (
        select(
            Brand.name.label("brand_name"),
            Theme.theme_type,
            Theme.aspect,
            Theme.mention_count,
            Theme.avg_sentiment,
        )
        .join(Brand, Brand.id == Theme.brand_id)
        .order_by(desc(Theme.mention_count))
        .limit(12)
    )
    if brand_ids:
        theme_query = theme_query.where(Theme.brand_id.in_(brand_ids))
    theme_rows = db.execute(theme_query).all()

    review_query = (
        select(
            Brand.name.label("brand_name"),
            Product.title.label("product_title"),
            Review.title,
            Review.content,
            Review.sentiment_score,
            Review.raw_payload,
        )
        .join(Product, Product.id == Review.product_id)
        .join(Brand, Brand.id == Product.brand_id)
        .order_by(desc(func.coalesce(Review.helpful_votes, 0)), desc(Review.created_at))
        .limit(8)
    )
    if brand_ids:
        review_query = review_query.where(Product.brand_id.in_(brand_ids))
    review_rows = db.execute(review_query).all()

    brands = [row["brand_name"] for row in comparison]
    citations: list[dict] = []

    for row in product_rows[:5]:
        citations.append(
            {
                "type": "product",
                "label": f"{row.brand_name} product",
                "url": row.url,
            }
        )

    for row in review_rows[:5]:
        raw_payload = row.raw_payload if isinstance(row.raw_payload, dict) else {}
        citations.append(
            {
                "type": "review",
                "label": f"{row.brand_name} review",
                "url": raw_payload.get("source_url") or raw_payload.get("reviews_page_url"),
            }
        )

    context = {
        "comparison": comparison,
        "top_products": [
            {
                "brand_name": row.brand_name,
                "title": row.title,
                "price": _safe_float(row.price),
                "discount_percent": _safe_float(row.discount_percent),
                "rating": _safe_float(row.rating),
                "review_count": row.review_count,
                "url": row.url,
            }
            for row in product_rows
        ],
        "themes": [
            {
                "brand_name": row.brand_name,
                "theme_type": row.theme_type,
                "aspect": row.aspect,
                "mention_count": row.mention_count,
                "avg_sentiment": _safe_float(row.avg_sentiment),
            }
            for row in theme_rows
        ],
        "review_samples": [
            {
                "brand_name": row.brand_name,
                "product_title": row.product_title,
                "title": row.title,
                "content": row.content[:280],
                "sentiment_score": _safe_float(row.sentiment_score),
                "source_url": (row.raw_payload or {}).get("source_url") if isinstance(row.raw_payload, dict) else None,
            }
            for row in review_rows
        ],
        "brands": brands,
        "citations": citations,
    }
    return context


def _fallback_answer(question: str, context: dict) -> str:
    # this helper returns a deterministic summary when llm is unavailable
    comparison = context.get("comparison", [])
    if not comparison:
        return "i do not have enough analyzed data in the current database to answer that yet."

    top_sentiment = max(comparison, key=lambda row: row.get("sentiment_score") or -999)
    top_price = max(comparison, key=lambda row: row.get("avg_price") or -999)
    top_discount = max(comparison, key=lambda row: row.get("avg_discount_pct") or -999)

    return (
        f"i could not use the llm provider for this answer, so here is a grounded summary from the current dataset. "
        f"highest sentiment brand is {top_sentiment['brand_name']} at {top_sentiment.get('sentiment_score')}. "
        f"highest average price brand is {top_price['brand_name']} at {top_price.get('avg_price')}. "
        f"highest average discount brand is {top_discount['brand_name']} at {top_discount.get('avg_discount_pct')} percent. "
        f"question asked: {question}"
    )


async def answer_data_question(db: Session, question: str, brand_ids: Optional[list[int]] = None) -> dict:
    # this function answers one user question from current analyzed db state
    context = _build_context(db, brand_ids)
    if not context["comparison"] and not context["top_products"]:
        return {
            "answer": "i do not have enough analyzed data in the current database yet. run scrape and analysis first.",
            "provider": None,
            "model": None,
            "brands": [],
            "citations": [],
        }

    system_prompt = (
        "you answer questions about an ecommerce intelligence dashboard. "
        "use only the provided dataset context. "
        "if the context is insufficient, say that clearly. "
        "do not invent missing metrics. "
        "prefer short concrete answers with numbers."
    )
    user_prompt = (
        f"question: {question}\n"
        f"context json: {json.dumps(context, ensure_ascii=False)}"
    )

    llm = LlmRouter()
    try:
        result = await llm.generate(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=700)
        return {
            "answer": result.get("content", "").strip(),
            "provider": result.get("provider"),
            "model": result.get("model"),
            "brands": context["brands"],
            "citations": context["citations"][:8],
        }
    except Exception:
        return {
            "answer": _fallback_answer(question, context),
            "provider": None,
            "model": None,
            "brands": context["brands"],
            "citations": context["citations"][:8],
        }
