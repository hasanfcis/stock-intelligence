from __future__ import annotations

from datetime import date as Date, timedelta

from sqlalchemy import select

from ..models.score import DailyReport, StockScore
from .db import get_session
from .models import ReportRunORM, StockScoreORM

# Score buckets for Phase 4 measurement (planning doc Section 17).
_BUCKETS = [
    ("90+", 90, 101),
    ("80-89", 80, 90),
    ("70-79", 70, 80),
    ("60-69", 60, 70),
    ("<60", 0, 60),
]


def save_report(report: DailyReport) -> int:
    """Persists a DailyReport as one ReportRunORM + one StockScoreORM per
    ticker. Returns the new report_run id."""
    with get_session() as session:
        run = ReportRunORM(
            date=report.date,
            universe_size=report.universe_size,
            market_context=report.market_context.model_dump(mode="json"),
        )
        session.add(run)
        session.flush()  # populates run.id before we reference it

        for score in report.scores:
            session.add(
                StockScoreORM(
                    report_run_id=run.id,
                    ticker=score.ticker,
                    as_of=score.as_of,
                    price=score.price,
                    catalyst_score=score.catalyst_score,
                    technical_score=score.technical_score,
                    sentiment_score=score.sentiment_score,
                    overall_score=score.overall_score,
                    action_category=score.action_category.value,
                    golden_cross=score.golden_cross,
                    death_cross=score.death_cross,
                    breakout=score.breakout,
                    catalyst_ids=score.catalyst_ids,
                    why_today=score.why_today,
                )
            )
        return run.id


def get_latest_scores_by_ticker(before: Date | None = None) -> dict[str, StockScoreORM]:
    """Returns the most recent persisted score per ticker (optionally
    strictly before a given date) — used by alerts/engine.py to diff today's
    report against yesterday's."""
    with get_session() as session:
        stmt = select(StockScoreORM).order_by(StockScoreORM.as_of.desc(), StockScoreORM.id.desc())
        if before is not None:
            stmt = stmt.where(StockScoreORM.as_of < before)
        rows = session.execute(stmt).scalars().all()

        latest: dict[str, StockScoreORM] = {}
        for row in rows:
            if row.ticker not in latest:
                session.expunge(row)
                latest[row.ticker] = row
        return latest


def get_recent_score_records(ticker: str | None = None, limit: int = 200) -> list[StockScoreORM]:
    with get_session() as session:
        stmt = select(StockScoreORM).order_by(StockScoreORM.as_of.desc()).limit(limit)
        if ticker:
            stmt = stmt.where(StockScoreORM.ticker == ticker.upper())
        rows = session.execute(stmt).scalars().all()
        for row in rows:
            session.expunge(row)
        return rows


def get_unmeasured_scores(min_age_days: int = 7) -> list[StockScoreORM]:
    """Scores old enough that a forward-return measurement window has
    plausibly closed, but that haven't been measured yet."""
    cutoff = Date.today() - timedelta(days=min_age_days)
    with get_session() as session:
        stmt = select(StockScoreORM).where(
            StockScoreORM.as_of <= cutoff,
            StockScoreORM.forward_5d_return.is_(None),
        )
        rows = session.execute(stmt).scalars().all()
        for row in rows:
            session.expunge(row)
        return rows


def update_forward_returns(
    score_id: int,
    forward_5d_return: float | None,
    forward_20d_return: float | None,
    measured_at,
) -> None:
    with get_session() as session:
        row = session.get(StockScoreORM, score_id)
        if row is None:
            return
        row.forward_5d_return = forward_5d_return
        row.forward_20d_return = forward_20d_return
        row.measured_at = measured_at


def compute_bucket_performance() -> list[dict]:
    """Matches the planning doc's Section 17 table: average forward returns
    and win rate, grouped by the score bucket the recommendation fell into."""
    with get_session() as session:
        stmt = select(StockScoreORM).where(StockScoreORM.forward_5d_return.is_not(None))
        rows = session.execute(stmt).scalars().all()

    results = []
    for label, low, high in _BUCKETS:
        bucket_rows = [r for r in rows if low <= r.overall_score < high]
        if not bucket_rows:
            results.append(
                {"bucket": label, "count": 0, "avg_5d_return": None, "avg_20d_return": None, "win_rate": None}
            )
            continue

        avg_5d = sum(r.forward_5d_return for r in bucket_rows) / len(bucket_rows)
        measured_20d = [r for r in bucket_rows if r.forward_20d_return is not None]
        avg_20d = (
            sum(r.forward_20d_return for r in measured_20d) / len(measured_20d)
            if measured_20d
            else None
        )
        wins = sum(1 for r in bucket_rows if r.forward_5d_return > 0)
        results.append(
            {
                "bucket": label,
                "count": len(bucket_rows),
                "avg_5d_return": round(avg_5d, 2),
                "avg_20d_return": round(avg_20d, 2) if avg_20d is not None else None,
                "win_rate": round(wins / len(bucket_rows) * 100, 1),
            }
        )
    return results
