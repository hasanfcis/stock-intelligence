import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml

from stock_intel.exclusions import apply_exclusions
from stock_intel.models.stock import Stock


def _write_config(tmp_path: Path, rules: list[dict]) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "exclusions.yaml").write_text(yaml.dump({"rules": rules}))
    return config_dir


def test_domicile_rule_excludes_only_listed_symbols(tmp_path):
    config_dir = _write_config(
        tmp_path,
        [
            {
                "id": "exclude_israeli_domiciled",
                "description": "Israeli-domiciled companies only.",
                "type": "domicile",
                "country": "IL",
                "symbols": ["WIX"],
            }
        ],
    )
    stocks = [
        Stock(symbol="WIX", name="Wix.com", category="software_ai"),
        Stock(symbol="NVDA", name="NVIDIA", category="semiconductors"),
    ]
    kept, excluded = apply_exclusions(stocks, config_dir)

    assert [s.symbol for s in kept] == ["NVDA"]
    assert excluded[0].symbol == "WIX"
    assert excluded[0].rule_id == "exclude_israeli_domiciled"


def test_company_with_israeli_operations_is_not_excluded_unless_listed(tmp_path):
    """A company merely having Israeli operations/employees must NOT be
    excluded — only an explicit domicile-rule symbol list can exclude it."""
    config_dir = _write_config(
        tmp_path,
        [
            {
                "id": "exclude_israeli_domiciled",
                "description": "Israeli-domiciled companies only.",
                "type": "domicile",
                "country": "IL",
                "symbols": [],  # NVDA has an Israeli R&D office but is not domiciled there
            }
        ],
    )
    stocks = [Stock(symbol="NVDA", name="NVIDIA", category="semiconductors")]
    kept, excluded = apply_exclusions(stocks, config_dir)

    assert [s.symbol for s in kept] == ["NVDA"]
    assert excluded == []


def test_primary_lender_rule_does_not_catch_non_lending_fintech(tmp_path):
    """A payments/fintech company that is not primarily a lender must not be
    excluded by the primary-lender rule."""
    config_dir = _write_config(
        tmp_path,
        [
            {
                "id": "exclude_primary_lenders",
                "description": "Primary interest-based lenders only.",
                "type": "business_model",
                "business_model": "primary_lender",
                "symbols": ["SOME_BANK"],  # a real bank/lender
            }
        ],
    )
    stocks = [
        Stock(symbol="SOME_BANK", name="Some Regional Bank", category="financials"),
        Stock(symbol="SQ", name="Block Inc (payments)", category="software_ai"),
    ]
    kept, excluded = apply_exclusions(stocks, config_dir)

    assert [s.symbol for s in kept] == ["SQ"]
    assert excluded[0].symbol == "SOME_BANK"


def test_no_duplicate_exclusion_when_symbol_matches_multiple_rules(tmp_path):
    config_dir = _write_config(
        tmp_path,
        [
            {"id": "rule_a", "description": "a", "type": "manual", "symbols": ["XYZ"]},
            {"id": "rule_b", "description": "b", "type": "manual", "symbols": ["XYZ"]},
        ],
    )
    stocks = [Stock(symbol="XYZ", name="Test Co", category="software_ai")]
    kept, excluded = apply_exclusions(stocks, config_dir)

    assert kept == []
    assert len(excluded) == 1
    assert excluded[0].rule_id == "rule_a"
