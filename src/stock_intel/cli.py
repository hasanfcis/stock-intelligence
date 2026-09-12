from __future__ import annotations

import argparse
from pathlib import Path

from .providers.mock import MockMarketDataProvider, MockNewsProvider
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

    args = parser.parse_args()

    if args.command == "run":
        tickers = args.watchlist.split(",") if args.watchlist else None
        report = build_daily_report(
            market_data=MockMarketDataProvider(),
            news=MockNewsProvider(),
            tickers=tickers,
        )
        out_path = Path(args.out)
        write_report(report, out_path)
        print(f"Wrote {out_path} ({len(report.scores)} stocks scored)")
        for s in report.scores:
            print(f"  {s.ticker:<6} {s.overall_score:>5.1f}  {s.action_category.value}")


if __name__ == "__main__":
    main()
