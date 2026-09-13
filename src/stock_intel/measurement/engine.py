"""Phase 4 measurement (Specification.md Section 17 / planning doc Section 17).

Looks up each unmeasured, sufficiently-old StockScore record, finds the
closing price closest to (as_of + N trading days) using whatever
MarketDataProvider is passed in, and writes the forward return back to the
DB. This is intentionally approximate for v1: trading days are estimated as
calendar days * 7/5, and it uses the first available bar on/after the
target date rather than an exact trading-calendar lookup.
"""
from __future__ import annotations

from datetime import date as Date, datetime, timedelta, timezone

from ..providers.base import MarketDataProvider
from ..persistence import repository
from ..persistence.models import StockScoreORM

_TRADING_TO_CALENDAR = 7 / 5  # rough weekday adjustment


def _price_on_or_after(market_data: MarketDataProvider, ticker: str, target_date: Date) -> float | None:
    lookback_days = (Date.today() - target_date).days + 15
    if lookback_days <= 0:
        return None
    try:
        series = market_data.get_price_history(ticker, lookback_days=lookback_days)
    except Exception:
        return None
    for bar in series.bars:
        bar_date = datetime.fromisoformat(bar.date).date()
        if bar_date >= target_date:
            return bar.close
    return series.bars[-1].close if series.bars else None


def measure_pending_scores(market_data: MarketDataProvider, min_age_days: int = 7) -> int:
    """Returns the number of records updated with a forward return this run."""
    pending: list[StockScoreORM] = repository.get_unmeasured_scores(min_age_days=min_age_days)
    updated = 0

    for record in pending:
        target_5d = record.as_of + timedelta(days=round(5 * _TRADING_TO_CALENDAR))
        target_20d = record.as_of + timedelta(days=round(20 * _TRADING_TO_CALENDAR))

        forward_5d_return = None
        forward_20d_return = None

        if Date.today() >= target_5d:
            price_5d = _price_on_or_after(market_data, record.ticker, target_5d)
            if price_5d is not None and record.price:
                forward_5d_return = round((price_5d / record.price - 1) * 100, 2)

        if Date.today() >= target_20d:
            price_20d = _price_on_or_after(market_data, record.ticker, target_20d)
            if price_20d is not None and record.price:
                forward_20d_return = round((price_20d / record.price - 1) * 100, 2)

        if forward_5d_return is not None:
            repository.update_forward_returns(
                score_id=record.id,
                forward_5d_return=forward_5d_return,
                forward_20d_return=forward_20d_return,
                measured_at=datetime.now(timezone.utc),
            )
            updated += 1

    return updated
