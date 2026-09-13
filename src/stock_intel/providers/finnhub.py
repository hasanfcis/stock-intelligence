"""Finnhub implementation of NewsProvider (Specification.md Section 4/14).

Requires FINNHUB_API_KEY env var. Finnhub's free tier covers company news,
which is enough to feed the catalyst engine's classification step.

Drop-in replacement for MockNewsProvider.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

from .base import NewsItem

_FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/company-news"


class FinnhubNewsProvider:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["FINNHUB_API_KEY"]

    def get_recent_news(self, ticker: str, since: datetime) -> list[NewsItem]:
        params = {
            "symbol": ticker,
            "from": since.date().isoformat(),
            "to": datetime.now(timezone.utc).date().isoformat(),
            "token": self.api_key,
        }
        resp = requests.get(_FINNHUB_NEWS_URL, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json() or []

        news = []
        for item in items:
            news.append(
                NewsItem(
                    ticker=ticker,
                    headline=item.get("headline", ""),
                    summary=item.get("summary", ""),
                    source_name=item.get("source", "Finnhub"),
                    url=item.get("url", ""),
                    published_at=datetime.fromtimestamp(item.get("datetime", 0), tz=timezone.utc),
                )
            )
        return news
