"""Phase 5 intelligent alerts (Specification.md Section 14 roadmap item 5).

Compares today's StockScore list against the most recently persisted scores
per ticker and raises an Alert for anything that crossed a threshold or
flipped a technical regime today — not for the steady-state condition
itself (a stock that was already in a golden cross yesterday doesn't
re-alert every day).
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..models.alert import Alert, AlertType
from ..models.catalyst import Catalyst, Impact
from ..models.score import StockScore
from ..persistence.models import StockScoreORM

_HIGH_IMPACT_CONFIDENCE_MIN = 0.6
_HIGH_IMPACT_LEVELS = {Impact.VERY_HIGH, Impact.HIGH}


def detect_alerts(
    current_scores: list[StockScore],
    previous_by_ticker: dict[str, StockScoreORM],
    thresholds: dict[str, float],
    catalysts_by_ticker: dict[str, list[Catalyst]] | None = None,
) -> list[Alert]:
    alerts: list[Alert] = []
    now = datetime.now(timezone.utc)
    catalysts_by_ticker = catalysts_by_ticker or {}

    for score in current_scores:
        prev = previous_by_ticker.get(score.ticker)

        # Score crossed into Strong Buy Setup / Avoid-Sell today.
        if score.overall_score >= thresholds["strong_buy_setup"] and (
            prev is None or prev.overall_score < thresholds["strong_buy_setup"]
        ):
            alerts.append(
                Alert(
                    ticker=score.ticker,
                    alert_type=AlertType.SCORE_CROSSED_INTO_STRONG_BUY,
                    message=f"{score.ticker} crossed into Strong Buy Setup ({score.overall_score:.0f}/100)",
                    created_at=now,
                    overall_score=score.overall_score,
                )
            )
        elif score.overall_score < thresholds["neutral"] and (
            prev is None or prev.overall_score >= thresholds["neutral"]
        ):
            alerts.append(
                Alert(
                    ticker=score.ticker,
                    alert_type=AlertType.SCORE_CROSSED_INTO_AVOID,
                    message=f"{score.ticker} dropped into Avoid/Sell ({score.overall_score:.0f}/100)",
                    created_at=now,
                    overall_score=score.overall_score,
                )
            )

        # Technical regime changes — only alert on the flip, not the steady state.
        if score.golden_cross and not (prev and prev.golden_cross):
            alerts.append(
                Alert(
                    ticker=score.ticker,
                    alert_type=AlertType.GOLDEN_CROSS,
                    message=f"{score.ticker}: 50-day crossed above the 200-day (golden cross)",
                    created_at=now,
                    overall_score=score.overall_score,
                )
            )
        if score.death_cross and not (prev and prev.death_cross):
            alerts.append(
                Alert(
                    ticker=score.ticker,
                    alert_type=AlertType.DEATH_CROSS,
                    message=f"{score.ticker}: 50-day crossed below the 200-day (death cross)",
                    created_at=now,
                    overall_score=score.overall_score,
                )
            )
        if score.breakout and not (prev and prev.breakout):
            alerts.append(
                Alert(
                    ticker=score.ticker,
                    alert_type=AlertType.NEW_BREAKOUT,
                    message=f"{score.ticker}: new breakout above resistance on volume",
                    created_at=now,
                    overall_score=score.overall_score,
                )
            )

        # New high-impact catalyst not present in yesterday's run — filtered
        # to catalysts that actually meet the high-impact/confidence bar
        # rather than alerting on every new headline.
        prev_catalyst_ids = set(prev.catalyst_ids) if prev else set()
        new_catalyst_ids = set(score.catalyst_ids) - prev_catalyst_ids
        new_high_impact = [
            c
            for c in catalysts_by_ticker.get(score.ticker, [])
            if c.id in new_catalyst_ids
            and c.impact in _HIGH_IMPACT_LEVELS
            and c.confidence >= _HIGH_IMPACT_CONFIDENCE_MIN
        ]
        if new_high_impact:
            top = max(new_high_impact, key=lambda c: c.confidence)
            alerts.append(
                Alert(
                    ticker=score.ticker,
                    alert_type=AlertType.HIGH_IMPACT_CATALYST,
                    message=f"{score.ticker}: {top.headline}",
                    created_at=now,
                    overall_score=score.overall_score,
                )
            )

    return alerts
