from __future__ import annotations

import argparse
from pathlib import Path

from .provider_factory import build_providers
from .report.builder import build_daily_report, write_report


def main() -> None:
    parser = argparse.ArgumentParser(prog="stock-intel")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run the pipeline once and print/save a daily report")
    run_cmd.add_argument(
        "--watchlist",
        type=str,
        default=None,
        help="Comma-separated tickers; defaults to the configured universe",
    )
    run_cmd.add_argument(
        "--out",
        type=str,
        default="daily_report.json",
        help="Path to write the JSON report",
    )
    run_cmd.add_argument(
        "--live",
        action="store_true",
        help="Use real providers (Alpaca/Finnhub/Claude) where configured, "
        "falling back to mocks for anything missing env vars",
    )
    run_cmd.add_argument(
        "--telegram",
        action="store_true",
        help="Send the report summary to Telegram after the run (requires "
        "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)",
    )

    args = parser.parse_args()

    if args.command == "run":
        tickers = args.watchlist.split(",") if args.watchlist else None
        market_data, news, sentiment_fn, macro_data = build_providers(args.live)

        kwargs = dict(market_data=market_data, news=news, macro_data=macro_data, tickers=tickers)
        if sentiment_fn is not None:
            kwargs["sentiment_fn"] = sentiment_fn

        report = build_daily_report(**kwargs)
        out_path = Path(args.out)
        write_report(report, out_path)
        print(f"Wrote {out_path} ({len(report.scores)} stocks scored)")
        for s in report.scores:
            print(f"  {s.ticker:<6} {s.overall_score:>5.1f}  {s.action_category.value}")

        if args.telegram:
            from .delivery.telegram import send_report_summary

            send_report_summary(report)


if __name__ == "__main__":
    main()
