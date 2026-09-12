"""Deterministic technical-indicator math.

Per Specification.md Section 4: an LLM never computes these numbers — it only
interprets/explains the output of this module. Everything here is pure,
side-effect-free math over a price series so it is trivially unit-testable
against known-answer fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Bar:
    date: str
    close: float
    high: float
    low: float
    volume: float


def sma(closes: list[float], period: int) -> float:
    if len(closes) < period:
        raise ValueError(f"Need at least {period} closes, got {len(closes)}")
    return sum(closes[-period:]) / period


def ema(closes: list[float], period: int) -> float:
    if len(closes) < period:
        raise ValueError(f"Need at least {period} closes, got {len(closes)}")
    k = 2 / (period + 1)
    ema_val = sum(closes[:period]) / period  # seed with SMA
    for price in closes[period:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


def rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        raise ValueError(f"Need at least {period + 1} closes, got {len(closes)}")
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float, float]:
    """Returns (macd_line, signal_line) using the final EMA values available."""
    if len(closes) < slow + signal:
        raise ValueError(f"Need at least {slow + signal} closes, got {len(closes)}")
    macd_series = []
    for end in range(slow, len(closes) + 1):
        window = closes[:end]
        macd_series.append(ema(window, fast) - ema(window, slow))
    signal_line = sma(macd_series, signal) if len(macd_series) >= signal else macd_series[-1]
    return macd_series[-1], signal_line


def rate_of_change(closes: list[float], period: int = 10) -> float:
    if len(closes) < period + 1:
        raise ValueError(f"Need at least {period + 1} closes, got {len(closes)}")
    past = closes[-period - 1]
    current = closes[-1]
    if past == 0:
        return 0.0
    return (current - past) / past * 100


def relative_strength(ticker_closes: list[float], benchmark_closes: list[float], period: int = 20) -> float:
    """Ticker % change vs benchmark % change over the trailing `period` bars."""
    if len(ticker_closes) < period + 1 or len(benchmark_closes) < period + 1:
        raise ValueError("Not enough bars for the requested relative-strength period")
    ticker_chg = (ticker_closes[-1] - ticker_closes[-period - 1]) / ticker_closes[-period - 1]
    bench_chg = (benchmark_closes[-1] - benchmark_closes[-period - 1]) / benchmark_closes[-period - 1]
    return (ticker_chg - bench_chg) * 100


def relative_volume(volumes: list[float], lookback: int = 20) -> float:
    if len(volumes) < lookback + 1:
        raise ValueError(f"Need at least {lookback + 1} volume bars, got {len(volumes)}")
    avg = sum(volumes[-lookback - 1 : -1]) / lookback
    if avg == 0:
        return 0.0
    return volumes[-1] / avg


def support_resistance(bars: list[Bar], lookback: int = 20) -> tuple[float, float]:
    """Simple support/resistance: trailing lowest low / highest high."""
    window = bars[-lookback:]
    if not window:
        raise ValueError("Need at least one bar")
    support = min(b.low for b in window)
    resistance = max(b.high for b in window)
    return support, resistance


def golden_death_cross(sma50: float, sma50_prev: float, sma200: float, sma200_prev: float) -> tuple[bool, bool]:
    golden = sma50_prev <= sma200_prev and sma50 > sma200
    death = sma50_prev >= sma200_prev and sma50 < sma200
    return golden, death
