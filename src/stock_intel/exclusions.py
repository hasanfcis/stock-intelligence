from __future__ import annotations

from pathlib import Path

from .config import CONFIG_DIR, load_exclusions_config
from .models.stock import Exclusion, Stock

# NOTE on the two nuanced rules called out in Specification.md Section 2:
#
# - "domicile" rules only exclude a company if it is INCORPORATED/PRIMARILY LISTED
#   in the given country. Having an office, R&D team, or employees there is a
#   separate fact and must never trigger this rule by itself.
#
# - "business_model: primary_lender" only excludes a company whose PRIMARY
#   revenue driver is interest-based lending (banks, consumer/commercial
#   lenders). Being "a financial company" (e.g., a payments processor,
#   exchange, or fintech that does not primarily lend) does not qualify.
#
# Both rules work off an explicit, maintained symbol list in exclusions.yaml
# rather than keyword-guessing from a company name or sector label, so the
# distinction is enforced by curation, not string matching.


def apply_exclusions(
    stocks: list[Stock], config_dir: Path = CONFIG_DIR
) -> tuple[list[Stock], list[Exclusion]]:
    """Split the universe into (kept, excluded), with an audit trail of why
    each excluded symbol was removed. Runs before any paid API or LLM calls."""
    cfg = load_exclusions_config(config_dir)
    rules = cfg.get("rules", [])

    excluded: list[Exclusion] = []
    excluded_symbols: set[str] = set()

    for rule in rules:
        rule_id = rule["id"]
        description = rule.get("description", "")
        for symbol in rule.get("symbols", []):
            if symbol in excluded_symbols:
                continue
            excluded_symbols.add(symbol)
            excluded.append(
                Exclusion(symbol=symbol, rule_id=rule_id, reason=description.strip())
            )

    kept = [s for s in stocks if s.symbol not in excluded_symbols]
    return kept, excluded
