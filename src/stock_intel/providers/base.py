"""Provider interfaces (Specification.md Section 4).

Any real data vendor (Alpaca, a news API, a filings API, etc.) implements one
of these Protocols and can be swapped in without touching pipeline code.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ..technical.indicators import Bar
from ..models.macro import MacroEvent


@dataclass
class NewsItem:
    ticker: str
    headline: str
    summary: str
    source_name: str
    url: str
    published_at: datetime


@dataclass
class Filing:
    ticker: str
    filing_type: str  # e.g. "8-K", "10-Q", "Form 4"
    summary: str
    url: str
    filed_at: datetime


@dataclass
class Fundamentals:
    ticker: str
    market_cap: float
    pe_ratio: float | None
    revenue_ttm: float | None


@dataclass
class PriceSeries:
    ticker: str
    bars: list[Bar]


class MarketDataProvider(Protocol):
    def get_price_history(self, ticker: str, lookback_days: int) -> PriceSeries: ...


class NewsProvider(Protocol):
    def get_recent_news(self, ticker: str, since: datetime) -> list[NewsItem]: ...


class FundamentalsProvider(Protocol):
    def get_fundamentals(self, ticker: str) -> Fundamentals: ...


class FilingsProvider(Protocol):
    def get_recent_filings(self, ticker: str, since: datetime) -> list[Filing]: ...


class MacroDataProvider(Protocol):
    def get_recent_macro_events(self, since: datetime) -> list[MacroEvent]: ...
