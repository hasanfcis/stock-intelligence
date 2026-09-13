"""Builds the (market_data, news, sentiment_fn, macro_data) tuple for a
pipeline run, falling back to mocks for any piece whose env vars/packages
aren't available. Shared by cli.py and delivery/scheduler.py so both entry
points pick providers the same way.
"""
from __future__ import annotations

from .providers.mock import MockMacroDataProvider, MockMarketDataProvider, MockNewsProvider


def build_providers(live: bool):
    if not live:
        return MockMarketDataProvider(), MockNewsProvider(), None, MockMacroDataProvider()

    market_data = MockMarketDataProvider()
    news = MockNewsProvider()
    sentiment_fn = None
    macro_data = MockMacroDataProvider()

    try:
        from .providers.alpaca import AlpacaMarketDataProvider

        market_data = AlpacaMarketDataProvider()
    except (KeyError, ImportError) as e:
        print(f"[warn] Alpaca market data unavailable ({e}); using mock prices")

    try:
        from .providers.finnhub import FinnhubNewsProvider

        news = FinnhubNewsProvider()
    except (KeyError, ImportError) as e:
        print(f"[warn] Finnhub news unavailable ({e}); using mock news")

    try:
        from .sentiment.llm_engine import score_sentiment_llm

        sentiment_fn = score_sentiment_llm
    except (KeyError, ImportError) as e:
        print(f"[warn] LLM sentiment unavailable ({e}); using rules-based sentiment")

    try:
        from .providers.fred import FredMacroDataProvider

        macro_data = FredMacroDataProvider()
    except (KeyError, ImportError) as e:
        print(f"[warn] FRED macro data unavailable ({e}); using mock macro events")

    return market_data, news, sentiment_fn, macro_data
