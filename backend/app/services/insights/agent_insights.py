# this file generates non obvious insights for decision makers
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models import Insight, Theme
from app.services.analysis.metrics import get_brand_comparison
from app.services.llm.router import LlmRouter, parse_json_from_text


def _heuristic_insights(comparison: list[dict]) -> list[dict]:
    # this function creates deterministic insights if llm is not available
    rows = [row for row in comparison if row.get("avg_price") is not None and row.get("sentiment_score") is not None]
    if not rows:
        return []

    best_value = sorted(rows, key=lambda x: x.get("value_for_money") or -999, reverse=True)[0]
    premium_with_sentiment = sorted(rows, key=lambda x: ((x.get("premium_index") or 0), (x.get("sentiment_score") or -999)), reverse=True)[0]
    most_discount = sorted(rows, key=lambda x: x.get("avg_discount_pct") or 0, reverse=True)[0]

    insights = [
        {
            "insight_type": "value",
            "title": f"{best_value['brand_name']} leads on value adjusted sentiment",
            "body": (
                f"this brand shows stronger sentiment relative to price than peers. "
                f"it indicates better value perception for the current price band."
            ),
            "confidence": 0.66,
            "payload": {"brand_id": best_value["brand_id"], "metric": "value_for_money"},
        },
        {
            "insight_type": "premium",
            "title": f"{premium_with_sentiment['brand_name']} sustains premium pricing without losing sentiment",
            "body": (
                "higher pricing does not automatically hurt customer perception here. "
                "this can support premium positioning with lower discount dependency."
            ),
            "confidence": 0.61,
            "payload": {"brand_id": premium_with_sentiment["brand_id"], "metric": "premium_index"},
        },
        {
            "insight_type": "discount",
            "title": f"{most_discount['brand_name']} appears discount dependent",
            "body": (
                "the brand shows the highest average discounting. if sentiment gain is weak, "
                "this may indicate promotional dependence instead of product pull."
            ),
            "confidence": 0.58,
            "payload": {"brand_id": most_discount["brand_id"], "metric": "avg_discount_pct"},
        },
    ]

    return insights


async def generate_and_store_insights(db: Session) -> int:
    # this function creates insight cards and stores latest set in db
    comparison = get_brand_comparison(db)
    if not comparison:
        return 0

    llm = LlmRouter()
    system_prompt = (
        "you are a market intelligence analyst for luggage brands. "
        "return strict json with key insights that are practical and non obvious."
    )
    user_prompt = (
        "given this brand comparison data create exactly 5 insights in json format: "
        "{\"insights\":[{\"insight_type\":\"value|premium|risk|opportunity|theme\",\"title\":\"...\",\"body\":\"...\",\"confidence\":0.0,\"payload\":{}}]} "
        f"data: {comparison}"
    )

    insights: list[dict] = []
    try:
        response = await llm.generate(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=900)
        parsed = parse_json_from_text(response.get("content", ""))
        if parsed and isinstance(parsed.get("insights"), list):
            insights = parsed["insights"]
    except Exception:
        insights = []

    if not insights:
        insights = _heuristic_insights(comparison)

    # this block resets old insights so ui always sees latest run
    db.query(Insight).delete(synchronize_session=False)

    count = 0
    for row in insights[:7]:
        if not row.get("title") or not row.get("body"):
            continue

        db.add(
            Insight(
                insight_type=row.get("insight_type", "analysis"),
                title=row["title"],
                body=row["body"],
                confidence=row.get("confidence"),
                payload=row.get("payload"),
            )
        )
        count += 1

    db.commit()
    return count
