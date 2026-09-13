"""Alpaca implementation of MarketDataProvider (Specification.md Section 4/14).

Requires ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY env vars. Uses Alpaca's
free IEX-feed EOD bars, which is enough for the daily technical engine.

This is a drop-in replacement for MockMarketDataProvider — nothing else in
the pipeline needs to change to use it.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests

from ..technical.indicators import Bar
from .base import PriceSeries

_ALPACA_DATA_URL = "https://data.alpaca.markets/v2/stocks/{symbol}/bars"


class AlpacaMarketDataProvider:
    def __init__(self, api_key_id: str | None = None, api_secret_key: str | None = None):
        self.api_key_id = api_key_id or os.environ["ALPACA_API_KEY_ID"]
        self.api_secret_key = api_secret_key or os.environ["ALPACA_API_SECRET_KEY"]

    def _headers(self) -> dict:
        return {
            "APCA-API-KEY-ID": self.api_key_id,
            "APCA-API-SECRET-KEY": self.api_secret_key,
        }

    def get_price_history(self, ticker: str, lookback_days: int) -> PriceSeries:
        # Fetch a wider calendar-day window since lookback_days is trading days.
        start = (datetime.now(timezone.utc) - timedelta(days=int(lookback_days * 1.6) + 10)).date()
        end = datetime.now(timezone.utc).date()

        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "timeframe": "1Day",
            "limit": 10000,
            "feed": "iex",
            "adjustment": "split",
        }
        resp = requests.get(
            _ALPACA_DATA_URL.format(symbol=ticker),
            headers=self._headers(),
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        bars = [
            Bar(
                date=b["t"][:10],
                close=b["c"],
                high=b["h"],
                low=b["l"],
                volume=b["v"],
            )
            for b in data.get("bars", [])
        ]
        if len(bars) > lookback_days:
            bars = bars[-lookback_days:]
        if not bars:
            raise ValueError(f"Alpaca returned no bars for {ticker} between {start} and {end}")
        return PriceSeries(ticker=ticker, bars=bars)
