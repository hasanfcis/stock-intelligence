from __future__ import annotations

import json
from datetime import date as Date, datetime, timezone
from pathlib import Path
from typing import Callable

from ..catalysts.engine import build_catalysts_for_stock
from ..config import CONFIG_DIR, load_macro_exposure_config, load_scoring_config
from ..exclusions import apply_exclusions
from ..macro.engine import build_macro_catalysts
from ..models.catalyst import Catalyst
from ..models.score import DailyReport, MarketContext, SentimentSnapshot
from ..providers.base import MacroDataProvider, MarketDataProvider, NewsProvider
from ..scoring.engine import build_stock_score
from ..sentiment.engine import score_sentiment as _default_score_sentiment
from ..technical.engine import build_technical_snapshot
from ..universe import get_universe

SentimentFn = Callable[[str, Date, list[Catalyst]], SentimentSnapshot]


def build_daily_report(
    market_data: MarketDataProvider,
    news: NewsProvider,
    macro_data: MacroDataProvider | None = None,
    tickers: list[str] | None = None,
    as_of: Date | None = None,
    config_dir: Path = CONFIG_DIR,
    sentiment_fn: SentimentFn = _default_score_sentiment,
    catalysts_out: dict[str, list[Catalyst]] | None = None,
) -> DailyReport:
    """catalysts_out, if given, is populated {ticker: [Catalyst, ...]} as a
    side effect — used by delivery/scheduler.py to feed the Phase 5 alert
    engine without re-running catalyst detection a second time.

    macro_data is optional: with no provider, the macro pipeline simply
    produces zero macro-derived catalysts rather than failing — callers
    that haven't wired one up yet (existing CLI/API paths) keep working."""
    as_of = as_of or datetime.now(timezone.utc).date()
    scoring_config = load_scoring_config(config_dir)
    macro_exposure_config = load_macro_exposure_config(config_dir)

    universe = get_universe(config_dir)
    if tickers:
        universe = [s for s in universe if s.symbol in set(tickers)]

    kept, excluded = apply_exclusions(universe, config_dir)

    spy_bars = market_data.get_price_history("SPY", lookback_days=260)
    sox_bars = market_data.get_price_history("SOX", lookback_days=260)
    spy_closes = [b.close for b in spy_bars.bars]
    sox_closes = [b.close for b in sox_bars.bars]

    # Macro Event -> Implication -> Exposure -> Catalyst pipeline runs once
    # for the whole universe (Section: macro-event addendum) — a CPI print
    # is one event, not one event per ticker, and only exposed categories
    # get a catalyst out of it at all.
    macro_catalysts_by_ticker: dict[str, list[Catalyst]] = {}
    if macro_data is not None:
        macro_events = macro_data.get_recent_macro_events(since=datetime.now(timezone.utc))
        macro_catalysts_by_ticker = build_macro_catalysts(macro_events, kept, macro_exposure_config)

    scores = []
    for stock in kept:
        price_series = market_data.get_price_history(stock.symbol, lookback_days=260)
        technical = build_technical_snapshot(
            stock.symbol, as_of, price_series.bars, spy_closes, sox_closes
        )

        own_news = news.get_recent_news(stock.symbol, since=datetime.now(timezone.utc))
        related_news = {
            sym: news.get_recent_news(sym, since=datetime.now(timezone.utc))
            for sym in stock.related_symbols
        }
        catalysts = build_catalysts_for_stock(stock, own_news, related_news)
        catalysts += macro_catalysts_by_ticker.get(stock.symbol, [])
        if catalysts_out is not None:
            catalysts_out[stock.symbol] = catalysts

        sentiment = sentiment_fn(stock.symbol, as_of, catalysts)

        score = build_stock_score(
            ticker=stock.symbol,
            as_of=as_of,
            price=price_series.bars[-1].close,
            catalysts=catalysts,
            technical=technical,
            sentiment=sentiment,
            scoring_config=scoring_config,
        )
        scores.append(score)

    scores.sort(key=lambda s: s.overall_score, reverse=True)
    negative = [s for s in scores if s.overall_score < scoring_config["thresholds"]["neutral"]]

    market_context = MarketContext(
        as_of=as_of,
        spx_change_pct=round((spy_closes[-1] / spy_closes[-2] - 1) * 100, 2),
        nasdaq_change_pct=round((spy_closes[-1] / spy_closes[-2] - 1) * 100, 2),  # placeholder until a NASDAQ series is wired in
        sox_change_pct=round((sox_closes[-1] / sox_closes[-2] - 1) * 100, 2),
        ten_year_yield=4.1,  # placeholder — Phase 2 wires a real rates provider
        vix=15.0,  # placeholder — Phase 2 wires a real vol provider
    )

    return DailyReport(
        date=as_of,
        universe_size=len(universe),
        excluded=[e.model_dump() for e in excluded],
        market_context=market_context,
        scores=scores,
        negative_catalysts=negative,
    )


def write_report(report: DailyReport, path: Path) -> None:
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
