# Stock Intelligence — Specification v0.1

## 1. Product Vision and Scope

**Vision:** A personal, daily research system that scans a configurable universe of
technology stocks, detects the catalysts that matter, scores each stock 0–100 using a
transparent blend of catalyst / technical / sentiment signals, and delivers a short,
evidence-backed morning briefing — with explicit "why today" reasoning instead of a bare
BUY/SELL call.

**In scope for v1:**
- A fixed starter universe (Section 2) with hard exclusion rules.
- A catalyst detection + tagging pipeline (news, filings, analyst actions).
- A deterministic technical-indicator engine (no LLM math).
- An LLM-assisted sentiment/narrative layer that must cite evidence.
- A configurable weighted scoring model producing `daily_report.json`.
- A CLI that runs the pipeline once per watchlist and prints/saves the report.
- A thin FastAPI service exposing the same pipeline over HTTP.

**Out of scope for v1** (see Section 13 roadmap): Telegram/email delivery, the web
dashboard, backtesting/history tracking, alerting, multi-user auth. These are Phase 2+.

## 2. Initial Universe

v1 ships with a small, hand-picked starter universe rather than the full catalog from the
planning doc, so the pipeline can be validated end-to-end quickly:

| Ticker | Category |
|---|---|
| NVDA | Semiconductors / AI compute |
| AMD | Semiconductors / AI compute |
| PLTR | Software / AI |
| TSLA | EV |
| ASML | Semiconductor equipment |
| AMAT | Semiconductor equipment |
| LRCX | Semiconductor equipment |
| KLAC | Semiconductor equipment |

The universe is stored as data (`universe.yaml`), not hard-coded, so tickers can be added
or removed without a code change. Categories are metadata used for industry-catalyst
propagation (Section 6), not hard filters.

### Exclusion rules (hard filters, run before any scoring)

- **Exclude:** Israeli-domiciled companies (by primary listing/incorporation, not by
  "has Israeli employees/offices") — configurable list, not a keyword/country guess.
- **Exclude:** Financial institutions / lenders whose *primary business* is interest-based
  lending (banks, consumer/commercial lenders). A fintech or payments company that is not
  primarily a lender is not auto-excluded.
- **Exclude:** any other user-defined sector, via the same config file.
- **Include:** U.S.-listed companies in software, semiconductors, AI, EV, biotech,
  robotics, and technology generally.

Exclusions run as a pre-filter (`exclusions.py`) against the universe before the pipeline
does any paid API calls or LLM calls — this saves cost and keeps the rule auditable
(each exclusion decision is logged with the rule that fired).

## 3. Repository Architecture

```
stock-intelligence/
├── SPECIFICATION.md
├── README.md
├── pyproject.toml
├── .env.example
├── config/
│   ├── universe.yaml          # tickers + category metadata
│   ├── exclusions.yaml        # exclusion rules
│   └── scoring_weights.yaml   # component weights, configurable
├── src/stock_intel/
│   ├── config.py              # loads + validates the YAML config
│   ├── universe.py            # universe loading, add/remove helpers
│   ├── exclusions.py          # hard-filter engine
│   ├── models/                # Pydantic data models (Section 4)
│   ├── catalysts/             # taxonomy + detection/tagging engine
│   ├── technical/             # deterministic indicator math
│   ├── sentiment/             # LLM-assisted narrative analysis
│   ├── scoring/               # combines the three engines into 0–100
│   ├── report/                # builds daily_report.json + summaries
│   ├── providers/             # MarketDataProvider / NewsProvider / etc. interfaces
│   ├── api/                   # FastAPI app
│   └── cli.py                 # `stock-intel run --watchlist NVDA,AMD,...`
├── examples/
│   └── daily_report_example.json
└── tests/
```

Each pipeline stage is a plain Python function/class with typed inputs and outputs, so it
can be tested in isolation and swapped later (e.g., replace the sentiment engine's LLM
call with a different model) without touching the rest of the pipeline.

## 4. Backend / API Architecture

**Stack:** Python 3.11+, FastAPI, Pydantic v2 for models, PostgreSQL for persistence
(Phase 2+ — v1 can run file/JSON-backed with no DB), APScheduler for the morning job once
automation starts (Phase 2).

**v1 API surface (FastAPI):**

- `POST /reports/run` — body: `{"tickers": ["NVDA","AMD",...]}` (optional; defaults to the
  configured universe). Runs the full pipeline synchronously and returns a `DailyReport`.
- `GET /universe` — returns the configured universe + exclusion rules in effect.
- `GET /reports/{ticker}` — returns the most recent cached `StockReport` for one ticker,
  if the pipeline has been run this session.

No auth in v1 (single-user, local/personal use). Add an API key header before any public
deployment (Section 12).

**Provider interfaces** (`providers/base.py`) — abstract base classes so a data vendor can
be swapped without touching pipeline code:

```python
class MarketDataProvider(Protocol):
    def get_price_history(self, ticker: str, lookback_days: int) -> PriceSeries: ...

class NewsProvider(Protocol):
    def get_recent_news(self, ticker: str, since: datetime) -> list[NewsItem]: ...

class FundamentalsProvider(Protocol):
    def get_fundamentals(self, ticker: str) -> Fundamentals: ...

class FilingsProvider(Protocol):
    def get_recent_filings(self, ticker: str, since: datetime) -> list[Filing]: ...
```

v1 ships a `MockProvider` for each interface (fixture data) so the pipeline is fully
testable without live API keys. A real provider (e.g., Alpaca for prices, a news API for
headlines) is a drop-in implementation of the same interface.

## 5. Data Models

Defined with Pydantic in `models/`:

- **`Stock`** — ticker, name, category, exchange, exclusion status + reason if excluded.
- **`Catalyst`** — id, ticker, `CatalystType` (Section 6 taxonomy), headline, summary,
  source URL, published_at, `direction` (positive/negative/mixed), `impact`
  (very_high/high/medium/low), `horizon` (immediate/short/medium/long), `confidence`
  (0–1), `evidence` (list of source snippets/URLs — never a bare claim, see Section 8).
- **`TechnicalSnapshot`** — ticker, as_of date, trend fields (EMA20, SMA50, SMA200,
  golden/death cross flag), momentum fields (RSI, MACD, ROC, relative strength vs
  SPY/sector ETF), volume fields (relative volume, breakout volume flag), price-structure
  fields (support, resistance, recent high/low, breakout/breakdown flags), and a derived
  `technical_score` (0–100).
- **`SentimentSnapshot`** — ticker, as_of date, `sentiment_score` (0–100),
  `direction_of_change` (improving/deteriorating/stable), `drivers` (list of catalyst ids
  it's attributed to — sentiment must be traceable to a catalyst, not "vibes").
- **`StockScore`** — ticker, catalyst_score, technical_score, sentiment_score,
  `overall_score`, weights used, `action_category` (Strong Buy Setup / Watch /
  Avoid-Sell), entry/stop/targets (optional — only populated when technicals support a
  defined level), risk_reward, thesis_vs_price (`company_quality`,
  `long_term_thesis`, `price_state`, `action`: WAIT/ENTER/TRIM), `why_today`
  (ranked list of the catalysts/technical facts driving today's score), confidence.
- **`DailyReport`** — date, universe snapshot, excluded tickers + reasons, list of
  `StockScore` (sorted), market context (SPY/QQQ/SOX/10Y/VIX), negative-catalyst
  watchlist.

All models are the single source of truth for both the CLI/API JSON output and (later)
the DB schema — the Postgres tables in Phase 2 are a direct mapping of these models plus
`id`/`created_at`.

## 6. Catalyst Taxonomy

`catalysts/taxonomy.py` defines a closed `CatalystType` enum so every catalyst is
classified consistently:

**Company-level:**
`EARNINGS_BEAT`, `EARNINGS_MISS`, `GUIDANCE_RAISE`, `GUIDANCE_CUT`, `PRODUCT_LAUNCH`,
`AI_ANNOUNCEMENT`, `MAJOR_CONTRACT`, `PARTNERSHIP`, `ACQUISITION`, `DIVESTITURE`,
`FDA_APPROVAL`, `FDA_REJECTION`, `CLINICAL_TRIAL_RESULT`, `CLINICAL_TRIAL_FAILURE`,
`SEC_FILING`, `INSIDER_BUY`, `INSIDER_SELL`, `ANALYST_UPGRADE`, `ANALYST_DOWNGRADE`,
`PRICE_TARGET_CHANGE`, `PRODUCT_DELAY`, `MANAGEMENT_CHANGE`, `LEGAL_REGULATORY`.

**Industry/macro-level** (attached to a ticker via the category graph, not just its own
news): `SECTOR_DEMAND_SIGNAL` (e.g., hyperscaler capex commentary that flows to NVDA/AMD),
`SUPPLY_CHAIN_SIGNAL`, `PEER_EARNINGS_READTHROUGH`, `MACRO_RATES`, `MACRO_REGULATORY`.

Each `CatalystType` has default `(direction, impact, horizon)` priors (a lookup table,
matching the example table in the planning doc) that the catalyst engine starts from and
the LLM/evidence can adjust per-instance — the defaults keep the system from treating
every headline as equally important by default.

The industry-catalyst graph for v1 is a small static mapping, e.g.:

```yaml
NVDA: [MSFT, AMZN, GOOGL, META, TSM, sox_index]   # hyperscaler capex + foundry readthrough
AMD: [MSFT, AMZN, GOOGL, META, TSM, sox_index]
ASML: [TSM, INTC, sox_index]
```

so a hyperscaler capex headline is tagged as a `SECTOR_DEMAND_SIGNAL` catalyst on NVDA and
AMD even though neither company was mentioned by name.

## 7. Impact / Confidence Scoring

Each `Catalyst` carries three independent dimensions, scored on fixed scales so they
combine predictably:

- **Direction:** `positive | negative | mixed` (mixed catalysts count toward magnitude but
  are excluded from the directional sum until resolved).
- **Impact magnitude:** `very_high=1.0, high=0.7, medium=0.4, low=0.15` — how much the
  catalyst could move the stock if true and durable.
- **Confidence:** 0–1, reflecting source quality and corroboration (an SEC filing or
  earnings call transcript starts high; a single unconfirmed social post starts low).
- **Horizon decay:** `immediate=1.0, short(≤1wk)=0.85, medium(≤1mo)=0.6, long=0.35` — a
  real but distant catalyst contributes less to *today's* score than the same catalyst
  landing today.

**Catalyst component score** for a ticker = weighted sum over its catalysts of
`direction_sign * impact_magnitude * confidence * horizon_decay`, normalized into 0–100
(clipped, with a configurable cap on how many catalysts count so one noisy day of 20 minor
headlines can't outweigh one very-high-impact catalyst).

**Technical component score**: deterministic composite of trend/momentum/volume/structure
sub-scores (weights configurable in `scoring_weights.yaml`), computed entirely in
`technical/indicators.py` — the LLM only *interprets and explains* this number, never
computes it.

**Sentiment component score**: the LLM reads news/filings/transcripts/commentary already
collected for the catalyst engine (not a separate scrape) and rates the *change* in
sentiment, always required to name the catalyst(s) driving the change (Section 8) —
sentiment with no attributable driver is capped at a neutral 50 rather than swinging the
score.

**Overall score** = `0.40*catalyst + 0.35*technical + 0.25*sentiment` by default
(configurable, per the planning doc's initial weights), then mapped to an
`action_category`:

| Score | Category |
|---|---|
| ≥ 80 | Strong Buy Setup |
| 60–79 | Watch |
| 40–59 | Neutral |
| < 40 | Avoid / Sell |

Category thresholds are also configurable, not hard-coded.

## 8. Evidence and Source Requirements

Every `Catalyst` and every sentiment claim must carry `evidence`: at least one
`(source_name, url, published_at)` tuple, plus a short reworded (not copy-pasted) summary
of what the source actually said. Concretely:

- The catalyst engine never emits a `Catalyst` without at least one source.
- The sentiment engine's LLM prompt requires it to cite which catalyst id(s) produced its
  sentiment read; free-floating sentiment claims are rejected by a validation step before
  they reach the scoring engine.
- The report builder surfaces a `sources[]` list per stock in the final JSON so any claim
  in the report can be traced back to where it came from.
- Any LLM step that summarizes text from a copyrighted source (news article, transcript)
  must paraphrase, never reproduce verbatim passages — this is enforced by prompt
  instructions and a light post-hoc similarity check in v1.1.

## 9. First Implementation Sprint (Phase 1 — Prototype)

Goal: given a hard-coded watchlist, produce a valid `daily_report.json` end to end, using
mock providers, in under two weeks of part-time work.

1. `models/` — all Pydantic models above, with a schema test that round-trips example
   JSON.
2. `universe.py` + `exclusions.py` + their YAML configs, with unit tests for the
   "Israeli company vs. Israeli operations" and "financial company vs. lender" edge
   cases explicitly called out in the planning doc.
3. `providers/base.py` interfaces + `MockMarketDataProvider` / `MockNewsProvider` with
   fixture data for NVDA, AMD, PLTR, TSLA, ASML, AMAT, LRCX, KLAC.
4. `technical/indicators.py` — EMA/SMA/RSI/MACD/ROC/relative-strength/support-resistance
   from the mock price series, with known-answer unit tests (e.g., RSI on a fixture
   series matches a hand-computed value).
5. `catalysts/engine.py` — turns mock news/filings into tagged `Catalyst` objects using
   the taxonomy + priors table.
6. `sentiment/engine.py` — v1 can start as a rules-based stand-in (keyword/direction
   heuristic tied to catalysts) so the pipeline is fully testable before wiring a real
   LLM call; the LLM call is a drop-in replacement behind the same interface.
7. `scoring/engine.py` — combines the three into `StockScore`, applies action-category
   thresholds and the thesis-vs-price logic.
8. `report/builder.py` — assembles `DailyReport`, writes `daily_report.json`.
9. `cli.py` — `python -m stock_intel run --watchlist NVDA,AMD,PLTR,TSLA` prints/saves the
   report.
10. Manually review the output for 2–4 weeks (per the planning doc) before automating.

## 10. Example API Output

`POST /reports/run` → `DailyReport` (trimmed to one stock for brevity):

```json
{
  "date": "2026-09-12",
  "universe_size": 8,
  "excluded": [],
  "market_context": {
    "spx_change_pct": 0.4,
    "sox_change_pct": 1.8,
    "ten_year_yield": 4.12,
    "vix": 14.3
  },
  "scores": [
    {
      "ticker": "NVDA",
      "price": 187.32,
      "catalyst_score": 94,
      "technical_score": 86,
      "sentiment_score": 88,
      "overall_score": 91,
      "action_category": "Strong Buy Setup",
      "why_today": [
        "Hyperscaler capex commentary flagged as sector demand signal (readthrough from MSFT earnings call)",
        "Price broke prior resistance on volume +180% vs 20-day average",
        "Two analyst price-target increases in the last 24h"
      ],
      "thesis_vs_price": {
        "company_quality": "excellent",
        "long_term_thesis": "bullish",
        "price_state": "fair",
        "action": "ENTER"
      },
      "entry": [182.0, 188.0],
      "stop": 174.5,
      "targets": [198.0, 212.0],
      "risk_reward": 3.2,
      "confidence": 0.78,
      "catalysts": ["cat_2026-09-12_nvda_001", "cat_2026-09-12_nvda_002"],
      "sources": [
        {"name": "Company IR release", "url": "https://...", "published_at": "2026-09-12T08:31:00Z"}
      ]
    }
  ],
  "negative_catalysts": []
}
```

The full example, including a second stock and the excluded-ticker shape, is in
`examples/daily_report_example.json`.

## 11. Testing Strategy

- **Unit tests** (`tests/`) for every deterministic component: indicator math against
  known-answer fixtures, exclusion-rule edge cases, catalyst-priors lookup, scoring-engine
  weight math (does `0.4/0.35/0.25` actually reduce to the expected overall score for a
  hand-picked input).
- **Contract tests** for provider interfaces: any new provider implementation is run
  against a shared test suite that checks it returns well-typed data, so swapping vendors
  can't silently break the pipeline.
- **Golden-file test** for the full pipeline: mock providers → `daily_report.json`,
  diffed against a committed golden file, run in CI on every PR.
- **Evidence validation tests**: assert that no `Catalyst` or sentiment claim can be
  constructed without at least one source (this is a model-level invariant, not just a
  convention).
- No live API calls in the test suite — everything runs against `Mock*Provider`s so tests
  are fast, free, and deterministic. Real-provider smoke tests are a separate, manually
  triggered CI job.

## 12. Deployment Direction

- **v1:** run locally via the CLI; no deployment needed yet.
- **Phase 2 (automation):** containerize (`Dockerfile` + `docker-compose.yml` with a
  Postgres service), run the morning pipeline via a scheduled job (cron container or
  APScheduler process), push the report to Telegram via a bot token and to email via
  SMTP/a transactional-email API.
- **Phase 3 (dashboard):** deploy the FastAPI backend (e.g., Fly.io/Render/a small VPS)
  behind an API key, deploy the Next.js frontend separately (e.g., Vercel), Postgres as a
  managed instance (e.g., Neon/Supabase/RDS).
- Secrets (data-provider keys, Telegram bot token, DB URL) via `.env`, never committed;
  `.env.example` documents required variables.
- Because this is a single-user personal tool, there's no need for multi-tenant auth —
  a single static API key header is sufficient once anything is network-reachable.

## 13. V1 Definition of Done

- [ ] Universe + exclusion config loads and validates; both documented edge cases
      (Israeli company vs. operations; financial vs. lender) have passing tests.
- [ ] Pipeline runs end-to-end on the 8-ticker starter universe using mock providers and
      produces a `daily_report.json` matching the `DailyReport` schema.
- [ ] Every catalyst and sentiment claim in the output carries at least one evidence
      source.
- [ ] Technical indicators are computed deterministically in code, not by an LLM, with
      known-answer tests passing.
- [ ] Scoring weights and action-category thresholds are read from
      `scoring_weights.yaml`, not hard-coded, and changing the file changes the output.
- [ ] `thesis_vs_price` correctly distinguishes "good company" from "good entry today" on
      at least one constructed fixture case (expensive stock, strong fundamentals →
      `WAIT`).
- [ ] CLI and FastAPI endpoint both produce identical output for the same input.
- [ ] Full test suite (unit + golden-file) passes in CI.
- [ ] README documents how to run the pipeline and how to plug in a real data provider.

## 14. Longer-Term Roadmap

- **Phase 2 — Automation:** real `MarketDataProvider`/`NewsProvider` implementations
  (e.g., Alpaca for prices; a news/filings API), scheduled daily run, Telegram + email
  delivery, Postgres persistence of every report for history.
- **Phase 3 — Dashboard:** Next.js + TypeScript site with the five screens from the
  planning doc (Dashboard, Stock page, Catalyst feed, Watchlist, History).
- **Phase 4 — Measurement:** track every recommendation's forward 5-day/20-day return and
  win rate by score bucket, surfaced back in the dashboard ("when this system has given a
  90+ score historically, what happened?").
- **Phase 5 — Intelligent alerts:** push notifications on new high-impact catalysts,
  technical regime changes (golden/death cross, breakout), or score crossing a threshold
  intraday.
- **Later:** expand the universe beyond the 8-ticker starter set to the full
  semiconductors/software/EV/biotech/other-tech categories from the original planning
  doc; weight optimization based on the tracked historical outcomes instead of the
  initial hand-picked weights.
