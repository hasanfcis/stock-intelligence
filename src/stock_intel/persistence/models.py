from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ReportRunORM(Base):
    """One row per pipeline run (Specification.md Section 3 DB schema — a
    direct mapping of the DailyReport model, per the spec's data-model
    section)."""

    __tablename__ = "report_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    universe_size: Mapped[int] = mapped_column(Integer)
    market_context: Mapped[dict] = mapped_column(JSON)


class StockScoreORM(Base):
    """One row per (ticker, as_of) — a direct mapping of the StockScore
    model. This is the table Phase 4 measurement/backtesting reads from."""

    __tablename__ = "stock_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_run_id: Mapped[int] = mapped_column(Integer, index=True)
    ticker: Mapped[str] = mapped_column(String, index=True)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    price: Mapped[float] = mapped_column(Float)
    catalyst_score: Mapped[float] = mapped_column(Float)
    technical_score: Mapped[float] = mapped_column(Float)
    sentiment_score: Mapped[float] = mapped_column(Float)
    overall_score: Mapped[float] = mapped_column(Float)
    action_category: Mapped[str] = mapped_column(String)
    golden_cross: Mapped[bool] = mapped_column(Boolean, default=False)
    death_cross: Mapped[bool] = mapped_column(Boolean, default=False)
    breakout: Mapped[bool] = mapped_column(Boolean, default=False)
    catalyst_ids: Mapped[list] = mapped_column(JSON, default=list)
    why_today: Mapped[list] = mapped_column(JSON, default=list)

    # Phase 4 measurement (Specification.md Section 17): filled in later,
    # once enough calendar time has passed, by measurement/engine.py.
    forward_5d_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    forward_20d_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
