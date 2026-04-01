# this file computes sentiment using rating and review text
from dataclasses import dataclass
from typing import Iterable, Optional

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()


@dataclass
class SentimentResult:
    # this data object holds score and label for one review
    score: float
    label: str


def _rating_score(rating: Optional[float]) -> float:
    # this function maps amazon star rating into a normalized range
    if rating is None:
        return 0.0
    bounded = max(1.0, min(5.0, float(rating)))
    return (bounded - 3.0) / 2.0


def _label_from_score(score: float) -> str:
    # this function maps numeric score to a readable class
    if score >= 0.2:
        return "positive"
    if score <= -0.2:
        return "negative"
    return "neutral"


def compute_review_sentiment(content: str, rating: Optional[float]) -> SentimentResult:
    # this function calculates one sentiment score from text and rating
    text_score = analyzer.polarity_scores(content or "").get("compound", 0.0)
    rating_score = _rating_score(rating)

    # this weighted blend stays stable when text is short or noisy
    combined = round((0.65 * text_score) + (0.35 * rating_score), 4)
    return SentimentResult(score=combined, label=_label_from_score(combined))


def aggregate_sentiment(scores: Iterable[float]) -> float:
    # this function returns average sentiment for a group of reviews
    values = [float(x) for x in scores if x is not None]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)
