from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Direction(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"


class Impact(str, Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Horizon(str, Enum):
    IMMEDIATE = "immediate"
    SHORT = "short"      # within ~1 week
    MEDIUM = "medium"    # within ~1 month
    LONG = "long"


class CatalystType(str, Enum):
    # Company-level
    EARNINGS_BEAT = "earnings_beat"
    EARNINGS_MISS = "earnings_miss"
    GUIDANCE_RAISE = "guidance_raise"
    GUIDANCE_CUT = "guidance_cut"
    PRODUCT_LAUNCH = "product_launch"
    AI_ANNOUNCEMENT = "ai_announcement"
    MAJOR_CONTRACT = "major_contract"
    PARTNERSHIP = "partnership"
    ACQUISITION = "acquisition"
    DIVESTITURE = "divestiture"
    FDA_APPROVAL = "fda_approval"
    FDA_REJECTION = "fda_rejection"
    CLINICAL_TRIAL_RESULT = "clinical_trial_result"
    CLINICAL_TRIAL_FAILURE = "clinical_trial_failure"
    SEC_FILING = "sec_filing"
    INSIDER_BUY = "insider_buy"
    INSIDER_SELL = "insider_sell"
    ANALYST_UPGRADE = "analyst_upgrade"
    ANALYST_DOWNGRADE = "analyst_downgrade"
    PRICE_TARGET_CHANGE = "price_target_change"
    PRODUCT_DELAY = "product_delay"
    MANAGEMENT_CHANGE = "management_change"
    LEGAL_REGULATORY = "legal_regulatory"

    # Industry / macro-level
    SECTOR_DEMAND_SIGNAL = "sector_demand_signal"
    SUPPLY_CHAIN_SIGNAL = "supply_chain_signal"
    PEER_EARNINGS_READTHROUGH = "peer_earnings_readthrough"
    MACRO_RATES = "macro_rates"
    MACRO_REGULATORY = "macro_regulatory"


# Default (direction, impact, horizon) priors per catalyst type.
# The catalyst engine starts from these and may adjust per-instance based on evidence.
CATALYST_PRIORS: dict[CatalystType, tuple[Direction, Impact, Horizon]] = {
    CatalystType.EARNINGS_BEAT: (Direction.POSITIVE, Impact.VERY_HIGH, Horizon.IMMEDIATE),
    CatalystType.EARNINGS_MISS: (Direction.NEGATIVE, Impact.VERY_HIGH, Horizon.IMMEDIATE),
    CatalystType.GUIDANCE_RAISE: (Direction.POSITIVE, Impact.HIGH, Horizon.SHORT),
    CatalystType.GUIDANCE_CUT: (Direction.NEGATIVE, Impact.HIGH, Horizon.SHORT),
    CatalystType.PRODUCT_LAUNCH: (Direction.POSITIVE, Impact.MEDIUM, Horizon.MEDIUM),
    CatalystType.AI_ANNOUNCEMENT: (Direction.POSITIVE, Impact.MEDIUM, Horizon.MEDIUM),
    CatalystType.MAJOR_CONTRACT: (Direction.POSITIVE, Impact.HIGH, Horizon.MEDIUM),
    CatalystType.PARTNERSHIP: (Direction.POSITIVE, Impact.MEDIUM, Horizon.MEDIUM),
    CatalystType.ACQUISITION: (Direction.POSITIVE, Impact.HIGH, Horizon.MEDIUM),
    CatalystType.DIVESTITURE: (Direction.MIXED, Impact.MEDIUM, Horizon.MEDIUM),
    CatalystType.FDA_APPROVAL: (Direction.POSITIVE, Impact.VERY_HIGH, Horizon.IMMEDIATE),
    CatalystType.FDA_REJECTION: (Direction.NEGATIVE, Impact.VERY_HIGH, Horizon.IMMEDIATE),
    CatalystType.CLINICAL_TRIAL_RESULT: (Direction.POSITIVE, Impact.VERY_HIGH, Horizon.IMMEDIATE),
    CatalystType.CLINICAL_TRIAL_FAILURE: (Direction.NEGATIVE, Impact.VERY_HIGH, Horizon.IMMEDIATE),
    CatalystType.SEC_FILING: (Direction.MIXED, Impact.LOW, Horizon.SHORT),
    CatalystType.INSIDER_BUY: (Direction.POSITIVE, Impact.MEDIUM, Horizon.MEDIUM),
    CatalystType.INSIDER_SELL: (Direction.NEGATIVE, Impact.LOW, Horizon.MEDIUM),
    CatalystType.ANALYST_UPGRADE: (Direction.POSITIVE, Impact.MEDIUM, Horizon.SHORT),
    CatalystType.ANALYST_DOWNGRADE: (Direction.NEGATIVE, Impact.MEDIUM, Horizon.SHORT),
    CatalystType.PRICE_TARGET_CHANGE: (Direction.MIXED, Impact.LOW, Horizon.SHORT),
    CatalystType.PRODUCT_DELAY: (Direction.NEGATIVE, Impact.HIGH, Horizon.MEDIUM),
    CatalystType.MANAGEMENT_CHANGE: (Direction.MIXED, Impact.MEDIUM, Horizon.MEDIUM),
    CatalystType.LEGAL_REGULATORY: (Direction.NEGATIVE, Impact.MEDIUM, Horizon.MEDIUM),
    CatalystType.SECTOR_DEMAND_SIGNAL: (Direction.POSITIVE, Impact.MEDIUM, Horizon.MEDIUM),
    CatalystType.SUPPLY_CHAIN_SIGNAL: (Direction.MIXED, Impact.MEDIUM, Horizon.MEDIUM),
    CatalystType.PEER_EARNINGS_READTHROUGH: (Direction.MIXED, Impact.MEDIUM, Horizon.SHORT),
    CatalystType.MACRO_RATES: (Direction.MIXED, Impact.MEDIUM, Horizon.SHORT),
    CatalystType.MACRO_REGULATORY: (Direction.MIXED, Impact.MEDIUM, Horizon.MEDIUM),
}


class Evidence(BaseModel):
    """Every catalyst/sentiment claim must be traceable to at least one of these."""

    source_name: str
    url: str
    published_at: datetime
    summary: str  # paraphrased, never a verbatim copy of the source text


class Catalyst(BaseModel):
    id: str
    ticker: str
    catalyst_type: CatalystType
    headline: str
    direction: Direction
    impact: Impact
    horizon: Horizon
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(min_length=1)
    is_industry_readthrough: bool = False
    source_ticker: str | None = None  # set when this catalyst was propagated from a related symbol

    @field_validator("evidence")
    @classmethod
    def require_evidence(cls, v: list[Evidence]) -> list[Evidence]:
        if not v:
            raise ValueError("A Catalyst must have at least one evidence source.")
        return v
