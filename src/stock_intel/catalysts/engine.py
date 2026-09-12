"""Catalyst detection + tagging (Specification.md Sections 6-8).

v1 tags mock/fixture news deterministically by keyword so the pipeline is
fully testable without an LLM call. A real implementation would replace
`_classify` with an LLM call constrained to return one of the CatalystType
values plus a confidence, but the interface (NewsItem -> Catalyst) stays the
same either way.
"""
from __future__ import annotations

from ..models.catalyst import CATALYST_PRIORS, Catalyst, CatalystType, Evidence
from ..models.stock import Stock
from ..providers.base import NewsItem

_KEYWORD_MAP: list[tuple[str, CatalystType]] = [
    ("capex", CatalystType.SECTOR_DEMAND_SIGNAL),
    ("infrastructure spending", CatalystType.SECTOR_DEMAND_SIGNAL),
    ("price target", CatalystType.PRICE_TARGET_CHANGE),
    ("raise price target", CatalystType.ANALYST_UPGRADE),
    ("contract", CatalystType.MAJOR_CONTRACT),
    ("accelerator", CatalystType.PRODUCT_LAUNCH),
    ("delivery estimate", CatalystType.ANALYST_DOWNGRADE),
    ("backlog", CatalystType.SUPPLY_CHAIN_SIGNAL),
    ("guidance", CatalystType.GUIDANCE_RAISE),
    ("earnings beat", CatalystType.EARNINGS_BEAT),
    ("fda", CatalystType.FDA_APPROVAL),
]


def _classify(item: NewsItem) -> CatalystType:
    text = f"{item.headline} {item.summary}".lower()
    for keyword, catalyst_type in _KEYWORD_MAP:
        if keyword in text:
            return catalyst_type
    return CatalystType.SEC_FILING  # low-impact default for unclassified items


def build_catalysts_for_stock(
    stock: Stock,
    own_news: list[NewsItem],
    related_news: dict[str, list[NewsItem]],
) -> list[Catalyst]:
    """Builds the Catalyst list for one stock: its own news plus any
    industry-readthrough catalysts propagated from related symbols
    (Specification.md Section 6's industry-catalyst graph)."""
    catalysts: list[Catalyst] = []

    for idx, item in enumerate(own_news):
        catalyst_type = _classify(item)
        direction, impact, horizon = CATALYST_PRIORS[catalyst_type]
        catalysts.append(
            Catalyst(
                id=f"cat_{stock.symbol.lower()}_{idx:03d}",
                ticker=stock.symbol,
                catalyst_type=catalyst_type,
                headline=item.headline,
                direction=direction,
                impact=impact,
                horizon=horizon,
                confidence=0.75,
                evidence=[
                    Evidence(
                        source_name=item.source_name,
                        url=item.url,
                        published_at=item.published_at,
                        summary=item.summary,
                    )
                ],
            )
        )

    for related_symbol, items in related_news.items():
        for idx, item in enumerate(items):
            base_type = _classify(item)
            # Readthrough catalysts are always tagged as sector/supply-chain
            # signals on the *related* stock, regardless of their type on the
            # source symbol, per Specification.md Section 6.
            catalyst_type = (
                CatalystType.SECTOR_DEMAND_SIGNAL
                if base_type != CatalystType.SUPPLY_CHAIN_SIGNAL
                else CatalystType.SUPPLY_CHAIN_SIGNAL
            )
            direction, impact, horizon = CATALYST_PRIORS[catalyst_type]
            catalysts.append(
                Catalyst(
                    id=f"cat_{stock.symbol.lower()}_readthrough_{related_symbol.lower()}_{idx:03d}",
                    ticker=stock.symbol,
                    catalyst_type=catalyst_type,
                    headline=f"[{related_symbol} readthrough] {item.headline}",
                    direction=direction,
                    impact=impact,
                    horizon=horizon,
                    confidence=0.55,  # readthrough catalysts start with lower confidence
                    evidence=[
                        Evidence(
                            source_name=item.source_name,
                            url=item.url,
                            published_at=item.published_at,
                            summary=item.summary,
                        )
                    ],
                    is_industry_readthrough=True,
                    source_ticker=related_symbol,
                )
            )

    return catalysts
