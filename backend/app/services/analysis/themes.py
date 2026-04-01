# this file extracts recurring praise and complaint themes
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class ThemeHit:
    # this object holds one grouped theme output
    aspect: str
    mention_count: int
    avg_sentiment: float
    sample_quotes: list[str]


ASPECT_KEYWORDS = {
    "wheels": ["wheel", "trolley", "rolling", "spinner"],
    "handle": ["handle", "grip", "pull rod", "stick"],
    "material": ["material", "fabric", "shell", "build"],
    "zipper": ["zip", "zipper", "chain"],
    "size": ["size", "fit", "cabin", "check in", "capacity"],
    "durability": ["durable", "durability", "broke", "broken", "quality"],
    "value": ["value", "price", "worth", "money"],
    "delivery": ["delivery", "packaging", "damage", "arrived"],
}

POSITIVE_HINTS = [
    "good",
    "great",
    "excellent",
    "smooth",
    "strong",
    "sturdy",
    "light",
    "spacious",
    "worth",
]

NEGATIVE_HINTS = [
    "bad",
    "poor",
    "worst",
    "broken",
    "damage",
    "cheap",
    "problem",
    "issue",
    "return",
    "refund",
]


def _find_aspects(text: str) -> list[str]:
    # this function tags review text with one or more aspects
    found = []
    lowered = text.lower()
    for aspect, keywords in ASPECT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            found.append(aspect)
    return found or ["general"]


def _theme_type(text: str, sentiment_score: Optional[float]) -> str:
    # this function classifies mention as praise or complaint
    lowered = text.lower()

    pos_hits = sum(1 for word in POSITIVE_HINTS if word in lowered)
    neg_hits = sum(1 for word in NEGATIVE_HINTS if word in lowered)

    if sentiment_score is not None:
        if sentiment_score >= 0.2 or pos_hits > neg_hits:
            return "praise"
        if sentiment_score <= -0.2 or neg_hits > pos_hits:
            return "complaint"

    if neg_hits > pos_hits:
        return "complaint"
    if pos_hits > neg_hits:
        return "praise"
    return "neutral"


def _clean_quote(text: str) -> str:
    # this function trims noise from sample quotes
    squeezed = re.sub(r"\s+", " ", text).strip()
    return squeezed[:220]


def extract_themes(reviews: Iterable[dict]) -> dict[str, list[ThemeHit]]:
    # this function groups review text into reusable themes
    buckets = defaultdict(lambda: defaultdict(lambda: {"sent": [], "quotes": []}))

    for review in reviews:
        text = (review.get("content") or "").strip()
        if not text:
            continue

        sentiment_score = review.get("sentiment_score")
        group = _theme_type(text, sentiment_score)
        if group == "neutral":
            continue

        for aspect in _find_aspects(text):
            item = buckets[group][aspect]
            if sentiment_score is not None:
                item["sent"].append(float(sentiment_score))
            if len(item["quotes"]) < 3:
                item["quotes"].append(_clean_quote(text))

    result: dict[str, list[ThemeHit]] = {"praise": [], "complaint": []}

    for group in ["praise", "complaint"]:
        for aspect, payload in buckets[group].items():
            count = len(payload["quotes"]) + max(0, len(payload["sent"]) - len(payload["quotes"]))
            avg_sent = round(sum(payload["sent"]) / len(payload["sent"]), 4) if payload["sent"] else 0.0
            result[group].append(
                ThemeHit(
                    aspect=aspect,
                    mention_count=max(count, 1),
                    avg_sentiment=avg_sent,
                    sample_quotes=payload["quotes"],
                )
            )

        result[group].sort(key=lambda x: x.mention_count, reverse=True)

    return result
