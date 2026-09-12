from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from ..exclusions import apply_exclusions
from ..models.score import DailyReport
from ..providers.mock import MockMarketDataProvider, MockNewsProvider
from ..report.builder import build_daily_report
from ..universe import get_universe

app = FastAPI(title="Stock Intelligence API", version="0.1.0")

_market_data = MockMarketDataProvider()
_news = MockNewsProvider()


class RunRequest(BaseModel):
    tickers: list[str] | None = None


@app.get("/universe")
def universe():
    stocks = get_universe()
    kept, excluded = apply_exclusions(stocks)
    return {
        "universe": [s.model_dump() for s in kept],
        "excluded": [e.model_dump() for e in excluded],
    }


@app.post("/reports/run", response_model=DailyReport)
def run_report(req: RunRequest) -> DailyReport:
    return build_daily_report(
        market_data=_market_data,
        news=_news,
        tickers=req.tickers,
    )
