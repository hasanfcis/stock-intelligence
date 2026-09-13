from __future__ import annotations

from datetime import date as Date

from ..models.catalyst import Catalyst, Direction, Horizon, Impact
from ..models.score import ActionCategory, StockScore, TechnicalSnapshot, SentimentSnapshot, ThesisVsPrice

_IMPACT_DEFAULT = {Impact.VERY_HIGH: 1.0, Impact.HIGH: 0.7, Impact.MEDIUM: 0.4, Impact.LOW: 0.15}
_HORIZON_DEFAULT = {Horizon.IMMEDIATE: 1.0, Horizon.SHORT: 0.85, Horizon.MEDIUM: 0.6, Horizon.LONG: 0.35}
_DIRECTION_SIGN = {Direction.POSITIVE: 1.0, Direction.NEGATIVE: -1.0, Direction.MIXED: 0.0}


def catalyst_component_score(
    catalysts: list[Catalyst],
    max_catalysts_counted: int = 8,
    impact_weights: dict[Impact, float] | None = None,
    horizon_decay: dict[Horizon, float] | None = None,
) -> float:
    """0-100 catalyst score (Specification.md Section 7)."""
    if not catalysts:
        return 50.0  # neutral when there's simply no news today

    impact_weights = impact_weights or _IMPACT_DEFAULT
    horizon_decay = horizon_decay or _HORIZON_DEFAULT

    ranked = sorted(
        catalysts,
        key=lambda c: impact_weights[c.impact] * c.confidence,
        reverse=True,
    )[:max_catalysts_counted]

    total = 0.0
    for c in ranked:
        total += (
            _DIRECTION_SIGN[c.direction]
            * impact_weights[c.impact]
            * c.confidence
            * horizon_decay[c.horizon]
        )
    # Normalize: max possible magnitude per catalyst is 1.0, so divide by count
    # counted, then map [-1, 1] -> [0, 100].
    normalized = max(-1.0, min(1.0, total / len(ranked)))
    return round(50 + normalized * 50, 1)


def overall_score(
    catalyst_score: float,
    technical_score: float,
    sentiment_score: float,
    weights: dict[str, float],
) -> float:
    return round(
        catalyst_score * weights["catalyst"]
        + technical_score * weights["technical"]
        + sentiment_score * weights["sentiment"],
        1,
    )


def action_category_for(score: float, thresholds: dict[str, float]) -> ActionCategory:
    if score >= thresholds["strong_buy_setup"]:
        return ActionCategory.STRONG_BUY_SETUP
    if score >= thresholds["watch"]:
        return ActionCategory.WATCH
    if score >= thresholds["neutral"]:
        return ActionCategory.NEUTRAL
    return ActionCategory.AVOID_SELL


def thesis_vs_price(
    catalyst_score: float,
    technical: TechnicalSnapshot,
    price: float,
) -> ThesisVsPrice:
    """Separates company/thesis quality from whether today's price is a good
    entry (Specification.md Section 7 / planning doc Section 18)."""
    company_quality = "excellent" if catalyst_score >= 75 else "good" if catalyst_score >= 55 else "fair" if catalyst_score >= 40 else "poor"
    long_term_thesis = "bullish" if catalyst_score >= 60 else "neutral" if catalyst_score >= 40 else "bearish"

    extended_above_resistance = (price - technical.resistance) / technical.resistance if technical.resistance else 0.0
    if extended_above_resistance > 0.10:
        price_state = "expensive"
    elif extended_above_resistance < -0.05:
        price_state = "cheap"
    else:
        price_state = "fair"

    if long_term_thesis == "bearish":
        action = "AVOID"
    elif price_state == "expensive":
        action = "WAIT"
    elif long_term_thesis == "bullish" and price_state in {"fair", "cheap"} and not technical.breakdown_risk:
        action = "ENTER"
    elif technical.breakdown_risk:
        action = "TRIM"
    else:
        action = "WAIT"

    return ThesisVsPrice(
        company_quality=company_quality,
        long_term_thesis=long_term_thesis,
        price_state=price_state,
        action=action,
    )


def build_why_today(catalysts: list[Catalyst], technical: TechnicalSnapshot, top_n: int = 3) -> list[str]:
    reasons: list[str] = []
    ranked = sorted(catalysts, key=lambda c: (_IMPACT_DEFAULT[c.impact], c.confidence), reverse=True)
    for c in ranked[:2]:
        reasons.append(c.headline)
    if technical.breakout:
        reasons.append(
            f"Price broke resistance (${technical.resistance:.2f}) on relative volume {technical.relative_volume:.1f}x average"
        )
    if technical.golden_cross:
        reasons.append("50-day moving average crossed above the 200-day (golden cross)")
    if technical.breakdown_risk:
        reasons.append(f"Price is testing support (${technical.support:.2f}) — breakdown risk")
    return reasons[:top_n] if reasons else ["No standout catalyst or technical signal today — routine session."]


def suggest_entry_stop_targets(technical: TechnicalSnapshot, price: float) -> tuple[tuple[float, float] | None, float | None, list[float], float | None]:
    """Only populated when technicals support a defined level, per the spec."""
    if technical.breakdown_risk:
        return None, None, [], None

    entry_low = round(min(price, technical.support * 1.02), 2)
    entry_high = round(max(price, technical.resistance * 1.01), 2)
    stop = round(technical.support * 0.97, 2)
    risk = (entry_high - stop) if entry_high > stop else None
    if not risk or risk <= 0:
        return (entry_low, entry_high), stop, [], None

    target1 = round(entry_high + risk * 2, 2)
    target2 = round(entry_high + risk * 3, 2)
    risk_reward = round((target1 - entry_high) / risk, 2)
    return (entry_low, entry_high), stop, [target1, target2], risk_reward


def build_stock_score(
    ticker: str,
    as_of: Date,
    price: float,
    catalysts: list[Catalyst],
    technical: TechnicalSnapshot,
    sentiment: SentimentSnapshot,
    scoring_config: dict,
) -> StockScore:
    catalyst_cfg = scoring_config.get("catalyst_scoring", {})
    c_score = catalyst_component_score(
        catalysts,
        max_catalysts_counted=catalyst_cfg.get("max_catalysts_counted", 8),
    )
    weights = scoring_config["weights"]
    o_score = overall_score(c_score, technical.technical_score, sentiment.sentiment_score, weights)
    category = action_category_for(o_score, scoring_config["thresholds"])
    tvp = thesis_vs_price(c_score, technical, price)
    why_today = build_why_today(catalysts, technical)
    entry, stop, targets, risk_reward = suggest_entry_stop_targets(technical, price)

    confidence = round(
        sum(c.confidence for c in catalysts) / len(catalysts) if catalysts else 0.5, 2
    )

    sources = [ev for c in catalysts for ev in c.evidence]

    return StockScore(
        ticker=ticker,
        as_of=as_of,
        price=price,
        catalyst_score=c_score,
        technical_score=technical.technical_score,
        sentiment_score=sentiment.sentiment_score,
        overall_score=o_score,
        weights_used=weights,
        action_category=category,
        why_today=why_today,
        thesis_vs_price=tvp,
        entry=entry,
        stop=stop,
        targets=targets,
        risk_reward=risk_reward,
        confidence=confidence,
        catalyst_ids=[c.id for c in catalysts],
        sources=sources,
        golden_cross=technical.golden_cross,
        death_cross=technical.death_cross,
        breakout=technical.breakout,
    )
