"""Deterministic mock providers (Specification.md Section 9, sprint step 3).

No network calls, no API keys — used by the CLI/API by default and by the
full test suite. A real provider is a drop-in replacement behind the same
Protocol in providers/base.py.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from ..technical.indicators import Bar
from ..models.catalyst import Evidence
from ..models.macro import MacroEvent, MacroIndicator
from .base import Fundamentals, NewsItem, PriceSeries

_SEED_OFFSETS = {
    "NVDA": 1, "AMD": 2, "PLTR": 3, "TSLA": 4,
    "ASML": 5, "AMAT": 6, "LRCX": 7, "KLAC": 8,
    "SPY": 100, "SOX": 101,
}


def _synthetic_bars(symbol: str, n_bars: int = 260, start_price: float = 150.0) -> list[Bar]:
    """A deterministic random walk with a mild upward drift, seeded per symbol
    so results are reproducible across runs."""
    rng = random.Random(_SEED_OFFSETS.get(symbol, hash(symbol) % 1000))
    price = start_price
    bars: list[Bar] = []
    today = datetime.now(timezone.utc).date()
    for i in range(n_bars):
        drift = 0.0006
        shock = rng.gauss(0, 0.018)
        price = max(1.0, price * (1 + drift + shock))
        high = price * (1 + abs(rng.gauss(0, 0.006)))
        low = price * (1 - abs(rng.gauss(0, 0.006)))
        volume = max(1_000_000, rng.gauss(8_000_000, 2_000_000))
        # Occasional volume spike to exercise breakout logic
        if i == n_bars - 1:
            volume *= 2.4
            price = high  # push the last close toward the day's high to simulate a breakout
        day = today - timedelta(days=(n_bars - i))
        bars.append(Bar(date=day.isoformat(), close=round(price, 2), high=round(high, 2), low=round(low, 2), volume=volume))
    return bars


class MockMarketDataProvider:
    def get_price_history(self, ticker: str, lookback_days: int) -> PriceSeries:
        bars = _synthetic_bars(ticker, n_bars=max(lookback_days, 260))
        return PriceSeries(ticker=ticker, bars=bars[-lookback_days:] if lookback_days < len(bars) else bars)


class MockNewsProvider:
    """Returns a small, deterministic set of headlines per ticker so the
    catalyst engine has something concrete to tag."""

    _FIXTURES: dict[str, list[dict]] = {
        "NVDA": [
            {
                "headline": "Hyperscaler flags higher AI infrastructure capex for next fiscal year",
                "summary": "A major cloud provider told investors on its earnings call that AI infrastructure spending would increase materially next year.",
                "source_name": "Company IR release",
                "url": "https://example.com/nvda-capex-readthrough",
            },
            {
                "headline": "Two analysts raise price targets after channel checks",
                "summary": "Sell-side coverage raised price targets citing stronger-than-expected data center demand checks.",
                "source_name": "Sell-side research note",
                "url": "https://example.com/nvda-pt-raises",
            },
        ],
        "AMD": [
            {
                "headline": "New AI accelerator sampling ahead of schedule",
                "summary": "The company said its next-generation AI accelerator is sampling with customers ahead of the previously communicated timeline.",
                "source_name": "Company press release",
                "url": "https://example.com/amd-accelerator",
            }
        ],
        "PLTR": [
            {
                "headline": "New multi-year government contract announced",
                "summary": "The company announced a new multi-year contract with a federal agency for its platform software.",
                "source_name": "Company press release",
                "url": "https://example.com/pltr-contract",
            }
        ],
        "TSLA": [
            {
                "headline": "Delivery estimate trimmed by one sell-side analyst",
                "summary": "An analyst lowered next-quarter delivery estimates citing softer regional demand data.",
                "source_name": "Sell-side research note",
                "url": "https://example.com/tsla-deliveries",
            }
        ],
        "ASML": [
            {
                "headline": "Lithography order backlog commentary from a foundry customer",
                "summary": "A major foundry customer indicated continued strong capital equipment orders for advanced nodes.",
                "source_name": "Industry news wire",
                "url": "https://example.com/asml-backlog",
            }
        ],
        "AMAT": [],
        "LRCX": [],
        "KLAC": [],
    }

    def get_recent_news(self, ticker: str, since: datetime) -> list[NewsItem]:
        items = []
        for i, fx in enumerate(self._FIXTURES.get(ticker, [])):
            items.append(
                NewsItem(
                    ticker=ticker,
                    headline=fx["headline"],
                    summary=fx["summary"],
                    source_name=fx["source_name"],
                    url=fx["url"],
                    published_at=datetime.now(timezone.utc) - timedelta(hours=i + 1),
                )
            )
        return items


class MockFundamentalsProvider:
    def get_fundamentals(self, ticker: str) -> Fundamentals:
        rng = random.Random(_SEED_OFFSETS.get(ticker, hash(ticker) % 1000))
        return Fundamentals(
            ticker=ticker,
            market_cap=rng.uniform(20e9, 3000e9),
            pe_ratio=rng.uniform(15, 90),
            revenue_ttm=rng.uniform(1e9, 100e9),
        )


class MockMacroDataProvider:
    """A single deterministic macro release per call — a CPI print that came
    in hotter than expected, matching the worked example in the planning
    doc/architecture diagram. Swap for a real provider (e.g. FRED, a
    calendar/consensus API) behind the same MacroDataProvider Protocol."""

    def get_recent_macro_events(self, since: datetime) -> list[MacroEvent]:
        return [
            MacroEvent(
                indicator=MacroIndicator.CPI,
                actual=3.2,
                expected=2.8,
                surprise=0.4,
                released_at=datetime.now(timezone.utc) - timedelta(hours=2),
                headline="CPI comes in hotter than expected at 3.2% vs. 2.8% consensus",
                evidence=Evidence(
                    source_name="BLS release",
                    url="https://example.com/cpi-release",
                    published_at=datetime.now(timezone.utc) - timedelta(hours=2),
                    summary="Headline CPI rose 3.2% year-over-year, above the 2.8% consensus estimate, reigniting rate-path uncertainty.",
                ),
            )
        ]
