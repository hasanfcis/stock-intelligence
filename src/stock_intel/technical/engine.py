from __future__ import annotations

from datetime import date as Date

from ..models.score import TechnicalSnapshot
from .indicators import (
    Bar,
    ema,
    golden_death_cross,
    macd,
    rate_of_change,
    relative_strength,
    relative_volume,
    rsi,
    sma,
    support_resistance,
)


def build_technical_snapshot(
    ticker: str,
    as_of: Date,
    bars: list[Bar],
    spy_closes: list[float],
    sector_closes: list[float],
) -> TechnicalSnapshot:
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]

    ema20 = ema(closes, 20)
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200) if len(closes) >= 200 else sma(closes, len(closes))
    sma50_prev = sma(closes[:-1], 50)
    sma200_prev = sma(closes[:-1], 200) if len(closes) - 1 >= 200 else sma(closes[:-1], len(closes) - 1)
    golden, death = golden_death_cross(sma50, sma50_prev, sma200, sma200_prev)

    rsi14 = rsi(closes, 14)
    macd_line, macd_signal = macd(closes)
    roc = rate_of_change(closes)
    rs_spy = relative_strength(closes, spy_closes)
    rs_sector = relative_strength(closes, sector_closes)
    rel_vol = relative_volume(volumes)
    support, resistance = support_resistance(bars)
    recent_high = max(b.high for b in bars[-20:])
    recent_low = min(b.low for b in bars[-20:])

    price = closes[-1]
    breakout = price > resistance * 0.999 and rel_vol > 1.5
    breakdown_risk = price < support * 1.001

    score = _composite_technical_score(
        price=price,
        sma50=sma50,
        sma200=sma200,
        golden_cross=golden,
        rsi14=rsi14,
        macd_line=macd_line,
        macd_signal=macd_signal,
        rel_vol=rel_vol,
        breakout=breakout,
        breakdown_risk=breakdown_risk,
        rs_sector=rs_sector,
    )

    return TechnicalSnapshot(
        ticker=ticker,
        as_of=as_of,
        ema20=ema20,
        sma50=sma50,
        sma200=sma200,
        golden_cross=golden,
        death_cross=death,
        rsi14=rsi14,
        macd=macd_line,
        macd_signal=macd_signal,
        rate_of_change=roc,
        relative_strength_spy=rs_spy,
        relative_strength_sector=rs_sector,
        relative_volume=rel_vol,
        volume_spike=rel_vol > 2.0,
        support=support,
        resistance=resistance,
        recent_high=recent_high,
        recent_low=recent_low,
        breakout=breakout,
        breakdown_risk=breakdown_risk,
        technical_score=score,
    )


def _composite_technical_score(
    *,
    price: float,
    sma50: float,
    sma200: float,
    golden_cross: bool,
    rsi14: float,
    macd_line: float,
    macd_signal: float,
    rel_vol: float,
    breakout: bool,
    breakdown_risk: bool,
    rs_sector: float,
) -> float:
    """Weighted composite over trend / momentum / volume / structure (0-100).

    This is intentionally simple and fully deterministic; sub-weights can be
    pulled into scoring_weights.yaml if they need to be tuned later.
    """
    trend = 50.0
    trend += 15 if price > sma50 else -15
    trend += 15 if price > sma200 else -15
    trend += 10 if golden_cross else 0
    trend = max(0.0, min(100.0, trend))

    momentum = 50.0
    momentum += (rsi14 - 50) * 0.6
    momentum += 10 if macd_line > macd_signal else -10
    momentum += max(-10.0, min(10.0, rs_sector * 0.5))
    momentum = max(0.0, min(100.0, momentum))

    volume = 50.0
    volume += max(-20.0, min(30.0, (rel_vol - 1.0) * 20))
    volume = max(0.0, min(100.0, volume))

    structure = 50.0
    structure += 25 if breakout else 0
    structure -= 25 if breakdown_risk else 0
    structure = max(0.0, min(100.0, structure))

    composite = trend * 0.35 + momentum * 0.35 + volume * 0.15 + structure * 0.15
    return round(composite, 1)
