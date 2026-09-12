from __future__ import annotations

from pathlib import Path

from .config import CONFIG_DIR, load_universe_config
from .models.stock import Stock


def get_universe(config_dir: Path = CONFIG_DIR) -> list[Stock]:
    """Load the configured universe, attaching each ticker's related symbols
    from the industry-catalyst propagation graph (Specification.md Section 6)."""
    cfg = load_universe_config(config_dir)
    links: dict[str, list[str]] = cfg.get("industry_links", {})
    stocks = []
    for entry in cfg.get("tickers", []):
        stocks.append(
            Stock(
                symbol=entry["symbol"],
                name=entry["name"],
                category=entry["category"],
                related_symbols=links.get(entry["symbol"], []),
            )
        )
    return stocks


def get_universe_symbols(config_dir: Path = CONFIG_DIR) -> list[str]:
    return [s.symbol for s in get_universe(config_dir)]
