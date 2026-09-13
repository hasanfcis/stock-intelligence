"""Runs the pipeline once a day at a fixed time (Specification.md Section
12 — Phase 2 automation), now also persisting to Postgres (Phase 4) and
raising Telegram alerts for anything that changed regime today (Phase 5).
Intended to run as a long-lived process inside the `scheduler` container in
docker-compose.yml.

Env vars:
  STOCK_INTEL_RUN_HOUR   hour (0-23, container-local time) to run at, default 8
  STOCK_INTEL_RUN_MINUTE minute, default 30
  STOCK_INTEL_OUT_PATH   where to write daily_report.json, default /app/data/daily_report.json
  DATABASE_URL           if set, persists each run and enables alerts/measurement
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from ..alerts.engine import detect_alerts
from ..models.catalyst import Catalyst
from ..provider_factory import build_providers
from ..report.builder import build_daily_report, write_report
from .telegram import send_alerts, send_report_summary


def run_once() -> None:
    market_data, news, sentiment_fn, macro_data = build_providers(live=True)
    kwargs = dict(market_data=market_data, news=news, macro_data=macro_data)
    if sentiment_fn is not None:
        kwargs["sentiment_fn"] = sentiment_fn

    catalysts_by_ticker: dict[str, list[Catalyst]] = {}
    report = build_daily_report(catalysts_out=catalysts_by_ticker, **kwargs)

    out_path = Path(os.environ.get("STOCK_INTEL_OUT_PATH", "/app/data/daily_report.json"))
    write_report(report, out_path)
    print(f"[scheduler] wrote {out_path} ({len(report.scores)} stocks scored)")

    _persist_and_alert(report, catalysts_by_ticker, market_data)

    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        try:
            send_report_summary(report)
        except Exception as e:  # noqa: BLE001 — a delivery failure shouldn't crash the scheduler
            print(f"[scheduler] Telegram delivery failed: {e}")


def _persist_and_alert(report, catalysts_by_ticker, market_data) -> None:
    """Phase 4 persistence + Phase 5 alerting. Both are no-ops (with a
    warning) if DATABASE_URL isn't set — the pipeline never depends on the
    DB being up to produce today's report."""
    from ..persistence import is_configured, init_db, repository

    if not is_configured():
        print("[scheduler] DATABASE_URL not set — skipping persistence, alerts, and measurement")
        return

    try:
        init_db()
        previous_by_ticker = repository.get_latest_scores_by_ticker(before=report.date)

        from ..config import load_scoring_config

        thresholds = load_scoring_config()["thresholds"]
        alerts = detect_alerts(report.scores, previous_by_ticker, thresholds, catalysts_by_ticker)

        repository.save_report(report)
        print(f"[scheduler] persisted {len(report.scores)} scores to the database")

        if alerts:
            print(f"[scheduler] {len(alerts)} alert(s) triggered")
            if os.environ.get("TELEGRAM_BOT_TOKEN"):
                try:
                    send_alerts(alerts)
                except Exception as e:  # noqa: BLE001
                    print(f"[scheduler] Telegram alert delivery failed: {e}")

        from ..measurement.engine import measure_pending_scores

        updated = measure_pending_scores(market_data)
        if updated:
            print(f"[scheduler] measured forward returns for {updated} past recommendation(s)")

    except Exception as e:  # noqa: BLE001 — a DB hiccup shouldn't crash the daily run
        print(f"[scheduler] persistence/alerts/measurement step failed: {e}")


def main() -> None:
    hour = int(os.environ.get("STOCK_INTEL_RUN_HOUR", "8"))
    minute = int(os.environ.get("STOCK_INTEL_RUN_MINUTE", "30"))

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_once, "cron", hour=hour, minute=minute)
    scheduler.start()
    print(f"[scheduler] started — daily run scheduled for {hour:02d}:{minute:02d} container time")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    main()
