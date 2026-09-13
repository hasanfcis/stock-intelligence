from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..exclusions import apply_exclusions
from ..models.score import DailyReport
from ..providers.mock import MockMacroDataProvider, MockMarketDataProvider, MockNewsProvider
from ..report.builder import build_daily_report
from ..universe import get_universe

app = FastAPI(title="Stock Intelligence API", version="0.1.0")

# The web dashboard (Specification.md Phase 3) runs on a different origin in
# dev (localhost:3000 vs :8000). Personal single-user tool, so a wide-open
# CORS policy is fine here — tighten this before any public deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_market_data = MockMarketDataProvider()
_news = MockNewsProvider()
_macro_data = MockMacroDataProvider()

# In-memory cache of the most recent run. Phase 4 replaces this with the
# Postgres-backed history the docker-compose `db` service is already
# provisioned for — the dashboard's /history endpoint below is a stub until
# then, per the README's "still to build" list.
_last_report: DailyReport | None = None


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
    global _last_report
    report = build_daily_report(
        market_data=_market_data,
        news=_news,
        macro_data=_macro_data,
        tickers=req.tickers,
    )
    _last_report = report

    from ..persistence import is_configured, init_db, repository

    if is_configured():
        try:
            init_db()
            repository.save_report(report)
        except Exception as e:  # noqa: BLE001 — an ad-hoc API run shouldn't fail on a DB hiccup
            print(f"[api] failed to persist report: {e}")

    return report


@app.get("/reports/latest", response_model=DailyReport)
def latest_report() -> DailyReport:
    if _last_report is None:
        raise HTTPException(
            status_code=404,
            detail="No report has been run yet. POST /reports/run first.",
        )
    return _last_report


@app.get("/stocks/{ticker}")
def stock_detail(ticker: str):
    if _last_report is None:
        raise HTTPException(status_code=404, detail="No report has been run yet.")
    ticker = ticker.upper()
    for score in _last_report.scores:
        if score.ticker == ticker:
            return score
    raise HTTPException(status_code=404, detail=f"{ticker} is not in the latest report.")


@app.get("/catalysts")
def catalyst_feed():
    """Flattens each stock's evidence sources into a single reverse-chronological
    feed for the dashboard's Catalyst feed screen (planning doc Section 11)."""
    if _last_report is None:
        return {"items": []}

    items = []
    for score in _last_report.scores:
        for source in score.sources:
            items.append(
                {
                    "ticker": score.ticker,
                    "source_name": source.source_name,
                    "url": source.url,
                    "published_at": source.published_at,
                    "summary": source.summary,
                }
            )
    items.sort(key=lambda i: i["published_at"], reverse=True)
    return {"items": items}


@app.get("/history")
def history():
    """Phase 4 (Specification.md Section 14): returns persisted recommendation
    history and performance-by-score-bucket, once DATABASE_URL is configured
    and at least one scheduler run has persisted + measured data. Falls back
    to an explicit empty state rather than erroring if the DB isn't set up."""
    from ..persistence import is_configured, repository

    if not is_configured():
        return {
            "items": [],
            "buckets": [],
            "note": "DATABASE_URL isn't configured — history isn't being persisted yet.",
        }

    try:
        records = repository.get_recent_score_records(limit=200)
        buckets = repository.compute_bucket_performance()
        return {
            "items": [
                {
                    "ticker": r.ticker,
                    "as_of": r.as_of.isoformat(),
                    "action_category": r.action_category,
                    "overall_score": r.overall_score,
                    "forward_5d_return": r.forward_5d_return,
                    "forward_20d_return": r.forward_20d_return,
                }
                for r in records
            ],
            "buckets": buckets,
        }
    except Exception as e:  # noqa: BLE001 — DB reachable-but-empty or connection hiccup
        return {"items": [], "buckets": [], "note": f"Could not read history: {e}"}
