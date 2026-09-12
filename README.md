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
