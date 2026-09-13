from __future__ import annotations

from datetime import date as Date
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from .catalyst import Evidence


class ActionCategory(str, Enum):
    STRONG_BUY_SETUP = "Strong Buy Setup"
    WATCH = "Watch"
    NEUTRAL = "Neutral"
    AVOID_SELL = "Avoid / Sell"


class TechnicalSnapshot(BaseModel):
    ticker: str
    as_of: Date
    ema20: float
    sma50: float
    sma200: float
    golden_cross: bool
    death_cross: bool
    rsi14: float
    macd: float
    macd_signal: float
    rate_of_change: float
    relative_strength_spy: float
    relative_strength_sector: float
    relative_volume: float
    volume_spike: bool
    support: float
    resistance: float
    recent_high: float
    recent_low: float
    breakout: bool
    breakdown_risk: bool
    technical_score: float = Field(ge=0, le=100)


class SentimentSnapshot(BaseModel):
    ticker: str
    as_of: Date
    sentiment_score: float = Field(ge=0, le=100)
    direction_of_change: str  # improving | deteriorating | stable
    drivers: list[str] = Field(default_factory=list)  # catalyst ids this is attributed to
    narrative: str  # short, paraphrased explanation

    @field_validator("direction_of_change")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        allowed = {"improving", "deteriorating", "stable"}
        if v not in allowed:
            raise ValueError(f"direction_of_change must be one of {allowed}")
        return v


class ThesisVsPrice(BaseModel):
    company_quality: str  # excellent | good | fair | poor
    long_term_thesis: str  # bullish | neutral | bearish
    price_state: str  # cheap | fair | expensive
    action: str  # ENTER | WAIT | TRIM | AVOID


class StockScore(BaseModel):
    ticker: str
    as_of: Date
    price: float
    catalyst_score: float = Field(ge=0, le=100)
    technical_score: float = Field(ge=0, le=100)
    sentiment_score: float = Field(ge=0, le=100)
    overall_score: float = Field(ge=0, le=100)
    weights_used: dict[str, float]
    action_category: ActionCategory
    why_today: list[str]
    thesis_vs_price: ThesisVsPrice
    entry: tuple[float, float] | None = None
    stop: float | None = None
    targets: list[float] = Field(default_factory=list)
    risk_reward: float | None = None
    confidence: float = Field(ge=0, le=1)
    catalyst_ids: list[str] = Field(default_factory=list)
    sources: list[Evidence] = Field(default_factory=list)
    # Technical regime flags, carried onto the score for Phase 5 alerting
    # (Specification.md Section 14) without needing to re-fetch the full
    # TechnicalSnapshot to detect a golden cross / breakout change.
    golden_cross: bool = False
    death_cross: bool = False
    breakout: bool = False


class MarketContext(BaseModel):
    as_of: Date
    spx_change_pct: float
    nasdaq_change_pct: float
    sox_change_pct: float
    ten_year_yield: float
    vix: float


class DailyReport(BaseModel):
    date: Date
    universe_size: int
    excluded: list[dict] = Field(default_factory=list)  # ticker -> reason, kept loose for the report layer
    market_context: MarketContext
    scores: list[StockScore]
    negative_catalysts: list[StockScore] = Field(default_factory=list)
