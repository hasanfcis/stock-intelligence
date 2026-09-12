from __future__ import annotations

from pydantic import BaseModel, Field


class Stock(BaseModel):
    """A single entry in the configured universe (Specification.md Section 2)."""

    symbol: str
    name: str
    category: str
    related_symbols: list[str] = Field(default_factory=list)


class Exclusion(BaseModel):
    """Records why a candidate symbol was filtered out before scoring."""

    symbol: str
    rule_id: str
    reason: str
