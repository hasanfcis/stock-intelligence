"""LLM-backed sentiment engine (Specification.md Section 5/7).

Drop-in replacement for sentiment.engine.score_sentiment: same signature,
same SentimentSnapshot output, so scoring/report code doesn't change.

Requires ANTHROPIC_API_KEY. The prompt requires the model to name which
catalyst id(s) drove its sentiment read — outputs that skip this are
rejected by the SentimentSnapshot validator (an unattributed claim is
capped as 'stable'/50, matching the rules-based fallback's behavior).
"""
from __future__ import annotations

import json
import os
from datetime import date as Date

import anthropic

from ..models.catalyst import Catalyst
from ..models.score import SentimentSnapshot
from .engine import score_sentiment as _rules_based_fallback

_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """You are a financial sentiment analyst. You will be given a list of \
tagged catalysts (headline, direction, impact, confidence) for one stock. Rate how \
sentiment has shifted TODAY, and you MUST attribute your rating to specific catalyst ids \
from the input — never invent a sentiment read with no supporting catalyst.

Respond ONLY with a JSON object, no preamble, no markdown fences:
{
  "sentiment_score": <0-100 float>,
  "direction_of_change": "improving" | "deteriorating" | "stable",
  "drivers": [<catalyst id strings from the input>],
  "narrative": "<1-2 sentence paraphrased explanation, never quoting source text verbatim>"
}
"""


def score_sentiment_llm(
    ticker: str,
    as_of: Date,
    catalysts: list[Catalyst],
    client: "anthropic.Anthropic | None" = None,
) -> SentimentSnapshot:
    if not catalysts:
        return _rules_based_fallback(ticker, as_of, catalysts)

    client = client or anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    payload = [
        {
            "id": c.id,
            "headline": c.headline,
            "direction": c.direction.value,
            "impact": c.impact.value,
            "confidence": c.confidence,
        }
        for c in catalysts
    ]

    response = client.messages.create(
        model=_MODEL,
        max_tokens=500,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    text = "".join(block.text for block in response.content if block.type == "text").strip()

    try:
        parsed = json.loads(text)
        drivers = [d for d in parsed.get("drivers", []) if d in {c.id for c in catalysts}]
        if not drivers:
            # No attributable driver named -> fall back rather than trust an
            # unsupported sentiment claim (Specification.md Section 8).
            return _rules_based_fallback(ticker, as_of, catalysts)

        return SentimentSnapshot(
            ticker=ticker,
            as_of=as_of,
            sentiment_score=float(parsed["sentiment_score"]),
            direction_of_change=parsed["direction_of_change"],
            drivers=drivers,
            narrative=parsed.get("narrative", ""),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        # Malformed LLM output -> fail safe to the deterministic fallback
        # rather than propagate a bad score.
        return _rules_based_fallback(ticker, as_of, catalysts)
