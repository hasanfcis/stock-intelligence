"""Sentiment/narrative engine (Specification.md Section 7-8).

v1 ships a rules-based stand-in that derives sentiment directly from the
already-tagged catalysts, so every sentiment claim is attributable by
construction (never "vibes"). Swapping in a real LLM call means replacing
`score_sentiment` with a call that reads the same catalysts + raw text and
returns a SentimentSnapshot with the same required `drivers` field —
the validation step below rejects anything else.
"""
from __future__ import annotations

from datetime import date as Date

from ..models.catalyst import Catalyst, Direction
from ..models.score import SentimentSnapshot

_DIRECTION_WEIGHT = {Direction.POSITIVE: 1.0, Direction.NEGATIVE: -1.0, Direction.MIXED: 0.0}


def score_sentiment(ticker: str, as_of: Date, catalysts: list[Catalyst]) -> SentimentSnapshot:
    if not catalysts:
        return SentimentSnapshot(
            ticker=ticker,
            as_of=as_of,
            sentiment_score=50.0,
            direction_of_change="stable",
            drivers=[],
            narrative="No catalysts with attributable sentiment signal today.",
        )

    weighted_sum = sum(
        _DIRECTION_WEIGHT[c.direction] * c.confidence for c in catalysts
    )
    normalized = max(-1.0, min(1.0, weighted_sum / max(1, len(catalysts))))
    score = round(50 + normalized * 50, 1)

    if normalized > 0.15:
        direction_of_change = "improving"
    elif normalized < -0.15:
        direction_of_change = "deteriorating"
    else:
        direction_of_change = "stable"

    drivers = [c.id for c in catalysts if c.direction != Direction.MIXED]
    top = sorted(catalysts, key=lambda c: c.confidence, reverse=True)[:2]
    narrative = "; ".join(f"{c.headline}" for c in top) or "No single dominant driver."

    return SentimentSnapshot(
        ticker=ticker,
        as_of=as_of,
        sentiment_score=score,
        direction_of_change=direction_of_change,
        drivers=drivers,
        narrative=narrative,
    )
