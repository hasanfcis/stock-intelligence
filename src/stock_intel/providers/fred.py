"""FRED implementation of MacroDataProvider (macro-event addendum).

Requires FRED_API_KEY (free, from https://fred.stlouisfed.org/docs/api/api_key.html).

Important limitation, stated plainly rather than faked: FRED publishes
*actual* released economic data, not economist consensus estimates. A true
"surprise vs. expected" (like the CPI example in the architecture) needs a
consensus/forecast feed (e.g. Econoday, TradingEconomics — typically paid).
This v1 provider approximates "expected" as the prior period's YoY reading,
which is a reasonable naive baseline but is NOT the same as a Wall Street
consensus number — treat `surprise` from this provider as directional
signal, not a precise beat/miss.

Only CPI is wired up for v1. FED_RATE_DECISION / JOBS_REPORT / GDP are real,
FRED-hosted series too (e.g. FEDFUNDS, PAYEMS, GDP) and can be added behind
the same method once a consensus source is picked — the MacroDataProvider
Protocol doesn't change either way.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

from ..models.catalyst import Evidence
from ..models.macro import MacroEvent, MacroIndicator

_FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
_CPI_SERIES_ID = "CPIAUCSL"  # CPI for All Urban Consumers, seasonally adjusted


class FredMacroDataProvider:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["FRED_API_KEY"]

    def get_recent_macro_events(self, since: datetime) -> list[MacroEvent]:
        params = {
            "series_id": _CPI_SERIES_ID,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 15,  # enough months to compute two YoY readings
        }
        resp = requests.get(_FRED_URL, params=params, timeout=15)
        resp.raise_for_status()
        obs = resp.json().get("observations", [])
        obs = [o for o in obs if o["value"] not in (".", "")]
        if len(obs) < 14:
            return []  # not enough history to compute YoY twice

        values = [float(o["value"]) for o in obs]  # index 0 = most recent
        latest_yoy = (values[0] / values[12] - 1) * 100
        prior_yoy = (values[1] / values[13] - 1) * 100  # naive "expected" baseline
        surprise = round(latest_yoy - prior_yoy, 2)

        released_at = datetime.fromisoformat(obs[0]["date"]).replace(tzinfo=timezone.utc)
        headline = (
            f"CPI YoY at {latest_yoy:.1f}% vs. {prior_yoy:.1f}% prior reading "
            f"({'accelerating' if surprise > 0 else 'decelerating'})"
        )

        return [
            MacroEvent(
                indicator=MacroIndicator.CPI,
                actual=round(latest_yoy, 2),
                expected=round(prior_yoy, 2),
                surprise=surprise,
                released_at=released_at,
                headline=headline,
                evidence=Evidence(
                    source_name="FRED (CPIAUCSL)",
                    url="https://fred.stlouisfed.org/series/CPIAUCSL",
                    published_at=released_at,
                    summary=headline,
                ),
            )
        ]
