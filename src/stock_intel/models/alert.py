from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class AlertType(str, Enum):
    SCORE_CROSSED_INTO_STRONG_BUY = "score_crossed_into_strong_buy"
    SCORE_CROSSED_INTO_AVOID = "score_crossed_into_avoid"
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"
    NEW_BREAKOUT = "new_breakout"
    HIGH_IMPACT_CATALYST = "high_impact_catalyst"


class Alert(BaseModel):
    ticker: str
    alert_type: AlertType
    message: str
    created_at: datetime
    overall_score: float | None = None
