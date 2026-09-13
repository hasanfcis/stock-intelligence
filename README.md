# Stock Intelligence

A personal daily stock-catalyst intelligence system. See [`SPECIFICATION.md`](./SPECIFICATION.md)
for the full design: universe/exclusions, catalyst taxonomy, scoring model, architecture,
and the phased roadmap.

## Status

**Phase 1 (prototype).** The pipeline runs end-to-end against deterministic mock data
providers and produces a `daily_report.json`. No live market-data/news API keys, no
database, no Telegram/email delivery yet — see `SPECIFICATION.md` Section 14 for what's
next.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run the pipeline

```bash
python -m stock_intel.cli run --watchlist NVDA,AMD,PLTR,TSLA --out daily_report.json
```

Or via the FastAPI service:

```bash
uvicorn stock_intel.api.main:app --reload
# then: curl -X POST localhost:8000/reports/run -H 'content-type: application/json' -d '{}'
```

Both entry points call the same `build_daily_report()` pipeline, so their output for the
same input is identical (see the V1 Definition of Done in the spec).

## Run the tests

```bash
pytest
```

`pip install -e ".[dev]"` includes SQLAlchemy, so the persistence/alert tests run against
a temp SQLite file with no Postgres required — same code path as production, different
database.

## Configuration

- `config/universe.yaml` — the ticker universe + the industry-catalyst propagation graph.
- `config/exclusions.yaml` — hard exclusion rules (see the domicile-vs-operations and
  lender-vs-fintech distinctions documented inline).
- `config/scoring_weights.yaml` — component weights, action-category thresholds, and
  catalyst-scoring caps/decay. Change this file to change scoring behavior — nothing is
  hard-coded in Python.

## Plugging in a real data provider

Implement one of the Protocols in `src/stock_intel/providers/base.py`
(`MarketDataProvider`, `NewsProvider`, `FundamentalsProvider`, `FilingsProvider`) and pass
it into `build_daily_report()` in place of the `Mock*Provider` implementations used by the
CLI/API today. No other pipeline code needs to change.

## Example output

See [`examples/daily_report_example.json`](./examples/daily_report_example.json) for a
worked example matching the `DailyReport` schema, and `SPECIFICATION.md` Section 10 for
commentary.

## Phase 2 — real providers, automation, delivery

Live providers are opt-in and fall back to mocks piece-by-piece if their env vars aren't
set, so you can turn them on one at a time:

```bash
pip install -e ".[live]"
cp .env.example .env   # fill in the keys you have
export $(grep -v '^#' .env | xargs)   # or use direnv/dotenv in your shell

python -m stock_intel.cli run --live --watchlist NVDA,AMD,PLTR,TSLA
```

- **Prices:** `providers/alpaca.py` — needs `ALPACA_API_KEY_ID` / `ALPACA_API_SECRET_KEY`
  (free Alpaca account, IEX feed is enough for daily bars).
- **News/catalysts:** `providers/finnhub.py` — needs `FINNHUB_API_KEY` (free tier company
  news endpoint).
- **Macro events:** `providers/fred.py` — needs `FRED_API_KEY` (free). CPI only for v1;
  see the module docstring for an important caveat (it approximates "expected" as the
  prior period's reading, since FRED has actuals but not consensus forecasts).
- **Sentiment:** `sentiment/llm_engine.py` — needs `ANTHROPIC_API_KEY`. Same
  `SentimentSnapshot` output as the rules-based engine; falls back to it automatically if
  the model's response doesn't name an attributable catalyst (Specification.md Section 8).
- **Telegram delivery:** `delivery/telegram.py` — needs `TELEGRAM_BOT_TOKEN` and
  `TELEGRAM_CHAT_ID`. Add `--telegram` to the CLI run, or it fires automatically from the
  scheduler below.

Any provider whose env vars are missing logs a `[warn]` line and silently uses its mock
counterpart instead — `--live` never hard-fails just because one key isn't set yet.

### Running the daily job automatically

`delivery/scheduler.py` is a small long-running process (APScheduler) that triggers the
pipeline once a day and pushes to Telegram if configured. `docker-compose.yml` wires it
up alongside a FastAPI service and Postgres:

```bash
docker compose up -d --build
```

This starts three containers:
- `db` — Postgres (for Phase 4 history/backtesting; the pipeline itself doesn't persist
  to it yet — see "Still to build" below)
- `api` — the FastAPI service on `:8000` for on-demand runs
- `scheduler` — runs the pipeline once a day at `STOCK_INTEL_RUN_HOUR:STOCK_INTEL_RUN_MINUTE`
  (container-local time, defaults 08:30) and delivers to Telegram

Reports land in `./data/daily_report.json` on the host (bind-mounted into both
containers).

### Where to deploy this

For a single-user personal tool, the cheapest path that still gets you "always on":

| Piece | Suggested host | Why |
|---|---|---|
| `api` + `scheduler` containers | Fly.io or Render | Free/cheap tier, `docker-compose`-style deploys, good for always-on small containers |
| Postgres | Neon or Supabase (managed) | Free tier, no ops; swap `DATABASE_URL` in `.env` and drop the `db` service from compose |
| Dashboard (Phase 3, not built yet) | Vercel | Trivial Next.js deploys later |

A single small VPS (e.g. a $5–6/mo Hetzner or DigitalOcean droplet) running
`docker compose up -d` directly is the simpler alternative if you'd rather have one box
instead of split managed services — just make sure `.env` never gets committed and the
Postgres port isn't exposed publicly if you go that route (drop the `ports: 5432:5432`
line in `docker-compose.yml` for anything beyond local dev).

### Still to build before Phase 2 is "done"

- Persisting each `DailyReport` to the `db` Postgres service (currently only written to
  the JSON file) — needed before Phase 4 backtesting has anything to query.
- Email delivery (SMTP/transactional API) — Telegram is wired, email isn't yet.
- API key auth on the FastAPI service before it's exposed on the public internet.

## Phase 3 — web dashboard

`web/` is a Next.js + TypeScript app implementing the five screens from the planning doc:
Dashboard, Stock page, Catalyst feed, Watchlist, History (History is a stub until Phase 4
persistence exists — see below).

```bash
cd web
npm install
cp .env.example .env   # NEXT_PUBLIC_API_URL, defaults to http://localhost:8000
npm run dev
```

It's a plain client of the FastAPI backend — start the API first (`uvicorn
stock_intel.api.main:app --reload` from the repo root, or `docker compose up`), run a
report (`POST /reports/run`, or `stock-intel run` writes to the file but the dashboard
reads from the API's in-memory `/reports/latest`, so trigger at least one run through the
API itself), then load the dashboard.

New backend endpoints added for the dashboard (`api/main.py`): `GET /reports/latest`,
`GET /stocks/{ticker}`, `GET /catalysts` (flattened source feed), `GET /history` (Phase 4
stub), plus CORS enabled for local dev.

`docker compose up -d --build` now also starts a `web` container on `:3000`. For an actual
deployment, Vercel is the simplest host for the Next.js piece (per the deployment table
above) — point its `NEXT_PUBLIC_API_URL` at wherever the `api` container ends up.

**Design:** dark, dense, terminal-style — hairline tables over cards, IBM Plex Sans/Mono,
amber for "watch," green/red reserved for gain/loss so color stays functional rather than
decorative. Numbers are the hero on every screen, not headlines.

**Not built yet:** the History screen's real data (Phase 4 persistence — see the
Phase 2 "still to build" list), and any auth in front of the dashboard/API.

## Phase 4 — measurement & backtesting

Every scheduler run now persists to Postgres and, once enough calendar time has passed,
measures how each recommendation actually performed.

- `persistence/` — SQLAlchemy models (`ReportRunORM`, `StockScoreORM`) and a
  `repository` module (`save_report`, `get_latest_scores_by_ticker`,
  `compute_bucket_performance`, etc.). All degrade gracefully: if `DATABASE_URL` isn't
  set, persistence/alerts/measurement are skipped with a log line rather than failing the
  run — the pipeline never depends on the DB being up.
- `measurement/engine.py` — for any score at least 7 calendar days old with no forward
  return yet, finds the closing price on/after `as_of + 5 trading days` (and `+20`) and
  writes the return back. This is intentionally approximate for v1 (calendar-day
  estimate of trading days, nearest-available-bar lookup) — good enough to start
  validating the scoring model, not a precise trading-calendar implementation.
- `GET /history` now returns real data once persistence has run for a while:
  per-recommendation forward returns and a performance-by-score-bucket table matching
  the planning doc's Section 17 example (count, avg 5-day/20-day return, win rate).
- The web dashboard's History screen renders this automatically — it still shows the
  honest empty state until there's enough measured history.

Nothing extra to run — persistence and measurement happen inside the existing
`scheduler` container once `DATABASE_URL` is set in `.env` (docker-compose already wires
this to the `db` service). For local (non-Docker) testing, set `DATABASE_URL` yourself
(SQLite works fine too, e.g. `sqlite:///./stock_intel.db`, useful for trying this without
Postgres running at all).

## Phase 5 — intelligent alerts

`alerts/engine.py` diffs today's scores against the most recently *persisted* scores per
ticker (so this also depends on `DATABASE_URL` being set) and raises an `Alert` for
anything that changed today, not for a steady-state condition:

- Score crossed into **Strong Buy Setup** or dropped into **Avoid/Sell**
- A **golden cross** or **death cross** happened today
- A new **breakout** triggered today
- A **new high-impact catalyst** appeared (impact `high`/`very_high` and confidence
  ≥ 0.6) that wasn't present in yesterday's run

Alerts fire automatically from the scheduler right after persistence, as a separate
Telegram message from the daily summary (`delivery/telegram.py`'s `send_alerts`). Nothing
to configure beyond `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`, already required for Phase 2
delivery.

## Macro event pipeline — a first-class path, not a catalyst subtype

Earlier versions had `MACRO_RATES`/`MACRO_REGULATORY` as taxonomy entries but no real
macro data source and no explicit translation step — a macro release was effectively
just another catalyst type. That's wrong: a CPI print isn't a fact about NVDA, it's an
economic surprise that has to be translated through a market-implication step and a
per-stock exposure lookup before it becomes a catalyst on anything. The pipeline is now:

```
CPI released (actual vs. expected)
        |
MacroEvent  (models/macro.py — a distinct model from Catalyst)
        |
market_implication()  ->  "hotter CPI -> rate-cut expectations pushed out ->
                            pressure on long-duration growth valuations"
        |
propagate_to_stocks()  ->  per-category exposure lookup (config/macro_exposure.yaml:
                            rate_sensitivity / growth_sensitivity, high/medium/low)
        |
Catalyst, only for exposed categories, tagged with the source MacroEvent's evidence
        |
merged into that stock's catalyst list (report/builder.py) before scoring/sentiment
```

**Key design point:** an unexposed category (e.g. something with `low` rate sensitivity)
gets *no* macro catalyst at all for a rate-driven surprise — the exclusion philosophy
that already governs which stocks enter the universe applies here too. A CPI print isn't
forced onto every stock; only categories flagged `high`/`medium` on the relevant
dimension in `config/macro_exposure.yaml` react.

- `models/macro.py` — `MacroEvent` (indicator, actual, expected, surprise, evidence).
  Deliberately a separate model from `Catalyst`, not a `CatalystType` value — see the
  module docstring.
- `macro/engine.py` — `market_implication()` (Event → Implication, independent of any
  one stock) and `propagate_to_stocks()` (Implication → per-category exposure →
  Catalyst). `build_macro_catalysts()` runs the whole pipeline for a report.
- `config/macro_exposure.yaml` — per-category sensitivity to rates and growth. Edit this
  file to change which categories react to which macro indicators, same pattern as
  `scoring_weights.yaml`.
- `providers/fred.py` — real CPI data via FRED (`FRED_API_KEY`). `providers/mock.py`'s
  `MockMacroDataProvider` ships a synthetic hot-CPI fixture for local dev/tests.
- Only CPI is wired to a real provider today. `FED_RATE_DECISION`, `JOBS_REPORT`, and
  `GDP` exist in the `MacroIndicator` enum and the exposure config, and
  `market_implication()` already handles all four — they just need a data source (FRED
  hosts `FEDFUNDS`/`PAYEMS`/`GDP` too; the gap is a consensus/forecast feed for a true
  surprise calculation, which FRED doesn't provide).

## Where things stand across all five phases

| Phase | Status |
|---|---|
| 1 — Prototype | Done. Mock providers, full pipeline, tests. |
| 2 — Automation | Done. Alpaca/Finnhub/Claude providers, Telegram, Docker/compose. Email still not built. |
| 3 — Dashboard | Done. Next.js app, 5 screens, backed by the FastAPI endpoints above. |
| 4 — Measurement | Done for v1. Persistence + approximate forward-return measurement + bucket stats. Precision improvements (exact trading-calendar lookups) are a good next iteration, not a blocker. |
| 5 — Alerts | Done. Telegram-delivered; a dedicated in-dashboard alerts screen would be a natural Phase 6 addition. |

**Known gaps worth tackling next, in rough priority order:** email delivery, API auth
before any public deployment, real data sources for the remaining macro indicators
(Fed/jobs/GDP — a consensus/forecast feed, specifically), and widening the universe
beyond the 8-ticker starter set per the original planning doc's full category list.
