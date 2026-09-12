import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from stock_intel.models.catalyst import Catalyst, CatalystType, Direction, Evidence, Horizon, Impact
from stock_intel.models.score import TechnicalSnapshot
from stock_intel.scoring.engine import (
    action_category_for,
    catalyst_component_score,
    overall_score,
    thesis_vs_price,
)


def _evidence():
    return [
        Evidence(
            source_name="Test Source",
            url="https://example.com",
            published_at=datetime.now(timezone.utc),
            summary="A paraphrased summary of the source.",
        )
    ]


def _catalyst(direction, impact, horizon, confidence=1.0):
    return Catalyst(
        id="cat_test",
        ticker="TEST",
        catalyst_type=CatalystType.EARNINGS_BEAT,
        headline="Test catalyst",
        direction=direction,
        impact=impact,
        horizon=horizon,
        confidence=confidence,
        evidence=_evidence(),
    )


def test_catalyst_score_no_catalysts_is_neutral():
    assert catalyst_component_score([]) == 50.0


def test_catalyst_score_strong_positive_catalyst_pushes_above_neutral():
    catalysts = [_catalyst(Direction.POSITIVE, Impact.VERY_HIGH, Horizon.IMMEDIATE)]
    score = catalyst_component_score(catalysts)
    assert score == 100.0  # max positive magnitude, full confidence, no decay


def test_catalyst_score_strong_negative_catalyst_pushes_below_neutral():
    catalysts = [_catalyst(Direction.NEGATIVE, Impact.VERY_HIGH, Horizon.IMMEDIATE)]
    score = catalyst_component_score(catalysts)
    assert score == 0.0


def test_overall_score_weight_math():
    weights = {"catalyst": 0.40, "technical": 0.35, "sentiment": 0.25}
    result = overall_score(catalyst_score=90, technical_score=80, sentiment_score=70, weights=weights)
    expected = round(90 * 0.40 + 80 * 0.35 + 70 * 0.25, 1)
    assert result == expected == 81.5


def test_action_category_thresholds():
    thresholds = {"strong_buy_setup": 80, "watch": 60, "neutral": 40}
    assert action_category_for(85, thresholds).value == "Strong Buy Setup"
    assert action_category_for(65, thresholds).value == "Watch"
    assert action_category_for(45, thresholds).value == "Neutral"
    assert action_category_for(20, thresholds).value == "Avoid / Sell"


def _technical(resistance=100.0, breakdown_risk=False):
    return TechnicalSnapshot(
        ticker="TEST",
        as_of=datetime.now(timezone.utc).date(),
        ema20=95, sma50=95, sma200=90,
        golden_cross=False, death_cross=False,
        rsi14=55, macd=1.0, macd_signal=0.5,
        rate_of_change=2.0,
        relative_strength_spy=1.0, relative_strength_sector=1.0,
        relative_volume=1.0, volume_spike=False,
        support=90.0, resistance=resistance,
        recent_high=resistance, recent_low=90.0,
        breakout=False, breakdown_risk=breakdown_risk,
        technical_score=70.0,
    )


def test_thesis_vs_price_good_company_expensive_price_means_wait():
    """The classic mistake the spec calls out: a great company at a stretched
    price should say WAIT, not ENTER."""
    technical = _technical(resistance=100.0)
    result = thesis_vs_price(catalyst_score=90, technical=technical, price=115.0)  # 15% above resistance
    assert result.company_quality == "excellent"
    assert result.long_term_thesis == "bullish"
    assert result.price_state == "expensive"
    assert result.action == "WAIT"


def test_thesis_vs_price_good_company_fair_price_means_enter():
    technical = _technical(resistance=100.0)
    result = thesis_vs_price(catalyst_score=90, technical=technical, price=98.0)
    assert result.action == "ENTER"


def test_thesis_vs_price_bearish_thesis_means_avoid():
    technical = _technical(resistance=100.0)
    result = thesis_vs_price(catalyst_score=20, technical=technical, price=98.0)
    assert result.long_term_thesis == "bearish"
    assert result.action == "AVOID"
