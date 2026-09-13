import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stock_intel.alerts.engine import detect_alerts
from stock_intel.models.alert import AlertType
from stock_intel.models.catalyst import Catalyst, CatalystType, Direction, Evidence, Horizon, Impact
from stock_intel.models.score import ActionCategory, StockScore, ThesisVsPrice
from stock_intel.persistence.models import StockScoreORM

_THRESHOLDS = {"strong_buy_setup": 80, "watch": 60, "neutral": 40}


def _score(ticker="NVDA", overall=85.0, golden_cross=False, death_cross=False, breakout=False, catalyst_ids=None):
    return StockScore(
        ticker=ticker,
        as_of=date.today(),
        price=100.0,
        catalyst_score=80,
        technical_score=80,
        sentiment_score=80,
        overall_score=overall,
        weights_used={"catalyst": 0.4, "technical": 0.35, "sentiment": 0.25},
        action_category=ActionCategory.STRONG_BUY_SETUP,
        why_today=["Test reason"],
        thesis_vs_price=ThesisVsPrice(
            company_quality="excellent", long_term_thesis="bullish", price_state="fair", action="ENTER"
        ),
        confidence=0.8,
        catalyst_ids=catalyst_ids or [],
        golden_cross=golden_cross,
        death_cross=death_cross,
        breakout=breakout,
    )


def _prev_orm(ticker="NVDA", overall=70.0, golden_cross=False, death_cross=False, breakout=False, catalyst_ids=None):
    return StockScoreORM(
        id=1,
        report_run_id=1,
        ticker=ticker,
        as_of=date.today(),
        price=95.0,
        catalyst_score=70,
        technical_score=70,
        sentiment_score=70,
        overall_score=overall,
        action_category="Watch",
        golden_cross=golden_cross,
        death_cross=death_cross,
        breakout=breakout,
        catalyst_ids=catalyst_ids or [],
        why_today=[],
    )


def test_first_ever_run_above_threshold_still_alerts():
    """With no history at all, a first-ever run above the strong-buy
    threshold still alerts (there's nothing to compare against, so 'crossed
    today' degrades to 'is currently above')."""
    scores = [_score(overall=85.0)]
    alerts = detect_alerts(scores, previous_by_ticker={}, thresholds=_THRESHOLDS)
    assert any(a.alert_type == AlertType.SCORE_CROSSED_INTO_STRONG_BUY for a in alerts)


def test_score_crossing_into_strong_buy_alerts():
    scores = [_score(overall=85.0)]
    previous = {"NVDA": _prev_orm(overall=70.0)}
    alerts = detect_alerts(scores, previous, _THRESHOLDS)
    assert len(alerts) == 1
    assert alerts[0].alert_type == AlertType.SCORE_CROSSED_INTO_STRONG_BUY


def test_score_staying_above_threshold_does_not_re_alert():
    scores = [_score(overall=85.0)]
    previous = {"NVDA": _prev_orm(overall=82.0)}  # already above 80 yesterday
    alerts = detect_alerts(scores, previous, _THRESHOLDS)
    assert alerts == []


def test_score_dropping_into_avoid_sell_alerts():
    scores = [_score(overall=35.0)]
    previous = {"NVDA": _prev_orm(overall=55.0)}
    alerts = detect_alerts(scores, previous, _THRESHOLDS)
    assert len(alerts) == 1
    assert alerts[0].alert_type == AlertType.SCORE_CROSSED_INTO_AVOID


def test_golden_cross_flip_alerts_once():
    scores = [_score(overall=50.0, golden_cross=True)]
    previous_no_cross = {"NVDA": _prev_orm(overall=50.0, golden_cross=False)}
    alerts = detect_alerts(scores, previous_no_cross, _THRESHOLDS)
    assert any(a.alert_type == AlertType.GOLDEN_CROSS for a in alerts)

    previous_already_crossed = {"NVDA": _prev_orm(overall=50.0, golden_cross=True)}
    alerts_again = detect_alerts(scores, previous_already_crossed, _THRESHOLDS)
    assert not any(a.alert_type == AlertType.GOLDEN_CROSS for a in alerts_again)


def _catalyst(cat_id, impact=Impact.VERY_HIGH, confidence=0.9):
    return Catalyst(
        id=cat_id,
        ticker="NVDA",
        catalyst_type=CatalystType.EARNINGS_BEAT,
        headline="Big beat",
        direction=Direction.POSITIVE,
        impact=impact,
        horizon=Horizon.IMMEDIATE,
        confidence=confidence,
        evidence=[
            Evidence(
                source_name="Test",
                url="https://example.com",
                published_at=datetime.now(timezone.utc),
                summary="A paraphrased summary.",
            )
        ],
    )


def test_new_high_impact_catalyst_alerts():
    scores = [_score(overall=50.0, catalyst_ids=["cat_new"])]
    previous = {"NVDA": _prev_orm(overall=50.0, catalyst_ids=["cat_old"])}
    catalysts_by_ticker = {"NVDA": [_catalyst("cat_new")]}

    alerts = detect_alerts(scores, previous, _THRESHOLDS, catalysts_by_ticker)
    assert any(a.alert_type == AlertType.HIGH_IMPACT_CATALYST for a in alerts)


def test_new_low_impact_catalyst_does_not_alert():
    scores = [_score(overall=50.0, catalyst_ids=["cat_new"])]
    previous = {"NVDA": _prev_orm(overall=50.0, catalyst_ids=["cat_old"])}
    catalysts_by_ticker = {"NVDA": [_catalyst("cat_new", impact=Impact.LOW, confidence=0.9)]}

    alerts = detect_alerts(scores, previous, _THRESHOLDS, catalysts_by_ticker)
    assert not any(a.alert_type == AlertType.HIGH_IMPACT_CATALYST for a in alerts)
