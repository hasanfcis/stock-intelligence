import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from stock_intel.models.score import ActionCategory, MarketContext, StockScore, DailyReport, ThesisVsPrice


def _fresh_db_module(tmp_path, monkeypatch):
    """Points DATABASE_URL at a temp SQLite file and resets the cached
    engine/session so each test starts from a clean database. SQLAlchemy is
    DB-agnostic, so this exercises the exact same repository code that runs
    against Postgres in production."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    from stock_intel.persistence import db as db_module

    db_module._engine = None
    db_module._SessionLocal = None
    db_module.init_db()
    return db_module


def _report(as_of, overall_score=85.0, ticker="NVDA"):
    return DailyReport(
        date=as_of,
        universe_size=1,
        excluded=[],
        market_context=MarketContext(
            as_of=as_of, spx_change_pct=0.1, nasdaq_change_pct=0.1, sox_change_pct=0.1, ten_year_yield=4.0, vix=15.0
        ),
        scores=[
            StockScore(
                ticker=ticker,
                as_of=as_of,
                price=100.0,
                catalyst_score=90,
                technical_score=85,
                sentiment_score=88,
                overall_score=overall_score,
                weights_used={"catalyst": 0.4, "technical": 0.35, "sentiment": 0.25},
                action_category=ActionCategory.STRONG_BUY_SETUP,
                why_today=["Test reason"],
                thesis_vs_price=ThesisVsPrice(
                    company_quality="excellent", long_term_thesis="bullish", price_state="fair", action="ENTER"
                ),
                confidence=0.8,
                catalyst_ids=["cat_1"],
            )
        ],
        negative_catalysts=[],
    )


def test_save_and_read_back_report(tmp_path, monkeypatch):
    _fresh_db_module(tmp_path, monkeypatch)
    from stock_intel.persistence import repository

    report = _report(as_of=date.today())
    repository.save_report(report)

    records = repository.get_recent_score_records(ticker="NVDA")
    assert len(records) == 1
    assert records[0].ticker == "NVDA"
    assert records[0].overall_score == 85.0
    assert records[0].forward_5d_return is None


def test_get_latest_scores_by_ticker_returns_most_recent(tmp_path, monkeypatch):
    _fresh_db_module(tmp_path, monkeypatch)
    from stock_intel.persistence import repository

    repository.save_report(_report(as_of=date.today() - timedelta(days=1), overall_score=60.0))
    repository.save_report(_report(as_of=date.today(), overall_score=90.0))

    latest = repository.get_latest_scores_by_ticker()
    assert latest["NVDA"].overall_score == 90.0


def test_bucket_performance_empty_until_measured(tmp_path, monkeypatch):
    _fresh_db_module(tmp_path, monkeypatch)
    from stock_intel.persistence import repository

    repository.save_report(_report(as_of=date.today()))
    buckets = repository.compute_bucket_performance()

    # No forward returns measured yet -> every bucket has zero count.
    assert all(b["count"] == 0 for b in buckets)


def test_update_forward_returns_populates_bucket(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    _fresh_db_module(tmp_path, monkeypatch)
    from stock_intel.persistence import repository

    repository.save_report(_report(as_of=date.today(), overall_score=85.0))
    record = repository.get_recent_score_records(ticker="NVDA")[0]

    repository.update_forward_returns(
        score_id=record.id,
        forward_5d_return=4.8,
        forward_20d_return=9.7,
        measured_at=datetime.now(timezone.utc),
    )

    buckets = repository.compute_bucket_performance()
    bucket_90 = next(b for b in buckets if b["bucket"] == "80-89")
    assert bucket_90["count"] == 1
    assert bucket_90["avg_5d_return"] == 4.8
    assert bucket_90["win_rate"] == 100.0
