"""Macro events are modeled separately from Catalyst on purpose.

Per the architecture: a macro release (CPI, a Fed decision, jobs, GDP) is
not itself a catalyst on any one stock — it's an economic surprise that
has to be translated through a market-implication step and a per-stock
exposure lookup before it becomes a Catalyst. Treating MacroEvent as a
first-class model (rather than shoving CPI into the same NewsItem/Catalyst
shape as "NVDA announced a product") is what keeps that translation step
honest instead of collapsing macro into "just another headline."
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from .catalyst import Evidence


class MacroIndicator(str, Enum):
    CPI = "cpi"
    FED_RATE_DECISION = "fed_rate_decision"
    JOBS_REPORT = "jobs_report"
    GDP = "gdp"


class MacroEvent(BaseModel):
    """A single macro release with its surprise vs. consensus. `surprise` is
    actual - expected, in the indicator's native units (e.g. +0.4 for a CPI
    print of 3.2% vs. 2.8% expected, or +25 for a 25bp larger-than-expected
    hike) — the sign convention is indicator-specific and interpreted by
    macro/engine.py, not assumed to always mean "bad" or "good"."""

    indicator: MacroIndicator
    actual: float
    expected: float
    surprise: float
    released_at: datetime
    headline: str
    evidence: Evidence
