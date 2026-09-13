import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stock_intel.macro.engine import build_macro_catalysts, market_implication, propagate_to_stocks
from stock_intel.models.catalyst import CatalystType, Direction, Evidence
from stock_intel.models.macro import MacroEvent, MacroIndicator
from stock_intel.models.stock import Stock

_EXPOSURE_CONFIG = {
    "categories": {
        "software_ai": {"rate_sensitivity": "high", "growth_sensitivity": "low"},
        "semi_equipment": {"rate_sensitivity": "medium", "growth_sensitivity": "medium"},
        "biotech_defensive_example": {"rate_sensitivity": "low", "growth_sensitivity": "low"},
    }
}


def _hot_cpi():
    return MacroEvent(
        indicator=MacroIndicator.CPI,
        actual=3.2,
        expected=2.8,
        surprise=0.4,
        released_at=datetime.now(timezone.utc),
        headline="CPI hotter than expected",
        evidence=Evidence(
            source_name="BLS",
            url="https://example.com/cpi",
            published_at=datetime.now(timezone.utc),
            summary="Headline CPI came in above consensus.",
        ),
    )


def _cool_cpi():
    return MacroEvent(
        indicator=MacroIndicator.CPI,
        actual=2.4,
        expected=2.8,
        surprise=-0.4,
        released_at=datetime.now(timezone.utc),
        headline="CPI cooler than expected",
        evidence=Evidence(
            source_name="BLS",
            url="https://example.com/cpi",
            published_at=datetime.now(timezone.utc),
            summary="Headline CPI came in below consensus.",
        ),
    )


def test_hot_cpi_is_negative_for_high_rate_sensitivity_category():
    implication = market_implication(_hot_cpi())
    assert implication.dimension == "rate_sensitivity"
    assert "pressure" in implication.narrative.lower()

    universe = [Stock(symbol="PLTR", name="Palantir", category="software_ai")]
    catalysts = propagate_to_stocks(implication, universe, _EXPOSURE_CONFIG)

    assert len(catalysts) == 1
    assert catalysts[0].direction == Direction.NEGATIVE
    assert catalysts[0].catalyst_type == CatalystType.MACRO_RATES
    assert catalysts[0].ticker == "PLTR"


def test_cool_cpi_is_positive_for_high_rate_sensitivity_category():
    implication = market_implication(_cool_cpi())
    universe = [Stock(symbol="PLTR", name="Palantir", category="software_ai")]
    catalysts = propagate_to_stocks(implication, universe, _EXPOSURE_CONFIG)

    assert len(catalysts) == 1
    assert catalysts[0].direction == Direction.POSITIVE


def test_unexposed_category_gets_no_macro_catalyst():
    """A category with 'low' sensitivity on the relevant dimension should
    not be forced to react to every CPI print — Specification.md's
    exclusion philosophy (don't force a reaction where none is warranted)
    applies to macro exposure too."""
    implication = market_implication(_hot_cpi())
    universe = [Stock(symbol="DEFENSIVE", name="Defensive Co", category="biotech_defensive_example")]
    catalysts = propagate_to_stocks(implication, universe, _EXPOSURE_CONFIG)
    assert catalysts == []


def test_unknown_category_is_skipped_not_erroring():
    implication = market_implication(_hot_cpi())
    universe = [Stock(symbol="UNKNOWN", name="Unknown Co", category="not_in_config")]
    catalysts = propagate_to_stocks(implication, universe, _EXPOSURE_CONFIG)
    assert catalysts == []


def test_medium_sensitivity_gets_medium_impact_catalyst():
    from stock_intel.models.catalyst import Impact

    implication = market_implication(_hot_cpi())
    universe = [Stock(symbol="ASML", name="ASML", category="semi_equipment")]
    catalysts = propagate_to_stocks(implication, universe, _EXPOSURE_CONFIG)

    assert len(catalysts) == 1
    assert catalysts[0].impact == Impact.MEDIUM


def test_build_macro_catalysts_groups_by_ticker():
    universe = [
        Stock(symbol="PLTR", name="Palantir", category="software_ai"),
        Stock(symbol="DEFENSIVE", name="Defensive Co", category="biotech_defensive_example"),
    ]
    by_ticker = build_macro_catalysts([_hot_cpi()], universe, _EXPOSURE_CONFIG)

    assert "PLTR" in by_ticker
    assert len(by_ticker["PLTR"]) == 1
    assert "DEFENSIVE" not in by_ticker


def test_every_macro_catalyst_carries_evidence_from_the_source_release():
    implication = market_implication(_hot_cpi())
    universe = [Stock(symbol="PLTR", name="Palantir", category="software_ai")]
    catalysts = propagate_to_stocks(implication, universe, _EXPOSURE_CONFIG)

    assert len(catalysts[0].evidence) == 1
    assert catalysts[0].evidence[0].source_name == "BLS"
