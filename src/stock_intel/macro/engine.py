"""Macro event pipeline — a first-class path parallel to company events, not
a catalyst type buried inside company news.

    CPI hotter than expected
            |
    MacroEvent (surprise = +0.4)
            |
    market_implication()  ->  "rate expectations up, growth-valuation pressure"
            |
    propagate_to_stocks()  ->  per-category exposure lookup (config/macro_exposure.yaml)
            |
    Catalyst per exposed stock, tagged is_macro_derived + source_macro_indicator

Only categories flagged "high"/"medium" exposure for the relevant dimension
get a catalyst at all — an unexposed category (Specification.md's exclusion
philosophy applies here too: don't force a reaction where none is
warranted) is skipped rather than given a diluted catalyst.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..models.catalyst import Catalyst, CatalystType, Direction, Horizon, Impact
from ..models.macro import MacroEvent, MacroIndicator
from ..models.stock import Stock

# Which exposure dimension each indicator acts through, and the direction
# convention: +1 means "a positive `surprise` value is bad for exposed
# growth/rate-sensitive names", -1 means the opposite.
_INDICATOR_DIMENSION = {
    MacroIndicator.CPI: ("rate_sensitivity", +1),  # hotter CPI -> hawkish -> bad for rate-sensitive growth
    MacroIndicator.FED_RATE_DECISION: ("rate_sensitivity", +1),  # bigger-than-expected hike -> bad
    MacroIndicator.JOBS_REPORT: ("rate_sensitivity", +1),  # much stronger jobs -> hawkish read -> mildly bad
    MacroIndicator.GDP: ("growth_sensitivity", -1),  # stronger GDP -> good for growth-cyclical names
}

_SENSITIVITY_TO_IMPACT = {"high": Impact.HIGH, "medium": Impact.MEDIUM, "low": None}
_EXPOSED_LEVELS = {"high", "medium"}


@dataclass
class MacroImplication:
    macro_event: MacroEvent
    narrative: str
    dimension: str  # "rate_sensitivity" | "growth_sensitivity"
    direction_sign: int  # +1 = bad for exposed names, -1 = good for exposed names


def market_implication(event: MacroEvent) -> MacroImplication:
    """Step 2 of the pipeline: what does this surprise actually mean,
    independent of any single stock — the same step your diagram calls
    'Rates expectations up / Growth-stock valuation pressure'."""
    dimension, sign = _INDICATOR_DIMENSION[event.indicator]
    surprise_direction = "hotter/larger than expected" if event.surprise > 0 else "cooler/smaller than expected"

    if event.indicator == MacroIndicator.CPI:
        narrative = (
            f"Inflation surprise: {event.surprise:+.1f}pp {surprise_direction} "
            f"-> rate-cut expectations pushed out -> pressure on long-duration growth valuations"
            if event.surprise > 0
            else f"Inflation surprise: {event.surprise:+.1f}pp {surprise_direction} "
            f"-> rate-cut expectations pulled forward -> relief for long-duration growth valuations"
        )
    elif event.indicator == MacroIndicator.FED_RATE_DECISION:
        narrative = f"Fed decision surprise: {event.surprise:+.0f}bp {surprise_direction} vs. consensus"
    elif event.indicator == MacroIndicator.JOBS_REPORT:
        narrative = f"Jobs report surprise: {event.surprise:+.0f}k {surprise_direction} -> hawkish/dovish repricing risk"
    else:  # GDP
        narrative = f"GDP surprise: {event.surprise:+.1f}pp {surprise_direction} -> growth backdrop shift"

    return MacroImplication(macro_event=event, narrative=narrative, dimension=dimension, direction_sign=sign)


def propagate_to_stocks(
    implication: MacroImplication,
    universe: list[Stock],
    exposure_config: dict,
) -> list[Catalyst]:
    """Step 3: per-stock exposure lookup + catalyst generation. This is the
    only place a MacroEvent turns into a Catalyst — company-level catalyst
    detection (catalysts/engine.py) never sees macro releases directly."""
    categories = exposure_config.get("categories", {})
    catalysts: list[Catalyst] = []

    for stock in universe:
        category_cfg = categories.get(stock.category)
        if not category_cfg:
            continue
        sensitivity = category_cfg.get(implication.dimension, "low")
        if sensitivity not in _EXPOSED_LEVELS:
            continue  # not exposed on this dimension -> no forced reaction

        impact = _SENSITIVITY_TO_IMPACT[sensitivity]
        raw_sign = 1 if implication.macro_event.surprise > 0 else -1
        effective_sign = raw_sign * implication.direction_sign
        direction = Direction.NEGATIVE if effective_sign > 0 else Direction.POSITIVE

        # Confidence scales with how large the surprise is relative to a
        # rough "notable surprise" scale per indicator, capped at 0.9 —
        # macro-derived catalysts stay slightly more conservative than a
        # confirmed company-specific event like an earnings beat.
        magnitude = min(1.0, abs(implication.macro_event.surprise) / _NOTABLE_SURPRISE[implication.macro_event.indicator])
        confidence = round(0.5 + magnitude * 0.4, 2)

        catalysts.append(
            Catalyst(
                id=f"cat_{stock.symbol.lower()}_macro_{implication.macro_event.indicator.value}_{implication.macro_event.released_at.date().isoformat()}",
                ticker=stock.symbol,
                catalyst_type=CatalystType.MACRO_RATES
                if implication.dimension == "rate_sensitivity"
                else CatalystType.MACRO_REGULATORY,
                headline=f"[Macro: {implication.macro_event.indicator.value.upper()}] {implication.narrative}",
                direction=direction,
                impact=impact,
                horizon=Horizon.SHORT,
                confidence=confidence,
                evidence=[implication.macro_event.evidence],
                is_industry_readthrough=True,  # macro flows through the same "not this company's own news" lens
                source_ticker=implication.macro_event.indicator.value,
            )
        )

    return catalysts


_NOTABLE_SURPRISE = {
    MacroIndicator.CPI: 0.3,  # +/- 0.3pp is already a notable CPI surprise
    MacroIndicator.FED_RATE_DECISION: 25.0,  # 25bp
    MacroIndicator.JOBS_REPORT: 100.0,  # 100k jobs
    MacroIndicator.GDP: 0.5,  # 0.5pp
}


def build_macro_catalysts(
    macro_events: list[MacroEvent],
    universe: list[Stock],
    exposure_config: dict,
) -> dict[str, list[Catalyst]]:
    """Runs the full Macro Event -> Implication -> Exposure -> Catalyst
    pipeline for every release, grouped by ticker so report/builder.py can
    merge these into each stock's catalyst list alongside company/industry
    catalysts."""
    by_ticker: dict[str, list[Catalyst]] = {}
    for event in macro_events:
        implication = market_implication(event)
        for catalyst in propagate_to_stocks(implication, universe, exposure_config):
            by_ticker.setdefault(catalyst.ticker, []).append(catalyst)
    return by_ticker
