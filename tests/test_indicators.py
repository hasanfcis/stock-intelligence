import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from stock_intel.technical.indicators import (
    Bar,
    ema,
    rate_of_change,
    relative_strength,
    relative_volume,
    rsi,
    sma,
    support_resistance,
)


def test_sma_known_answer():
    assert sma([1, 2, 3, 4, 5], 5) == 3.0
    assert sma([10, 20, 30], 2) == 25.0


def test_sma_raises_on_insufficient_data():
    with pytest.raises(ValueError):
        sma([1, 2], 5)


def test_ema_seeds_with_sma_then_smooths():
    closes = [10, 10, 10, 10, 10, 20]  # 5-period EMA seed = 10, then one shock
    result = ema(closes, 5)
    # k = 2/6 = 0.3333; ema = 20*0.3333 + 10*0.6667 = 13.333...
    assert result == pytest.approx(13.333, abs=0.01)


def test_rsi_all_gains_is_100():
    closes = [10 + i for i in range(20)]  # strictly increasing
    assert rsi(closes, 14) == pytest.approx(100.0)


def test_rsi_all_losses_is_zero():
    closes = [30 - i for i in range(20)]  # strictly decreasing
    assert rsi(closes, 14) == pytest.approx(0.0, abs=0.01)


def test_rsi_flat_series_is_neutral_when_no_losses():
    # A perfectly flat series has zero avg_loss -> RSI defined as 100 by convention here
    closes = [10.0] * 20
    assert rsi(closes, 14) == 100.0


def test_rate_of_change_known_answer():
    closes = [100] * 10 + [110]
    assert rate_of_change(closes, period=10) == pytest.approx(10.0)


def test_relative_strength_outperformance():
    ticker = [100] * 20 + [120]
    benchmark = [100] * 20 + [105]
    rs = relative_strength(ticker, benchmark, period=20)
    assert rs == pytest.approx(15.0, abs=0.01)  # 20% - 5% = 15pp outperformance


def test_relative_volume_spike_detected():
    volumes = [1_000_000] * 20 + [3_000_000]
    assert relative_volume(volumes, lookback=20) == pytest.approx(3.0)


def test_support_resistance_from_bars():
    bars = [
        Bar(date=f"2026-01-{i:02d}", close=100 + i, high=105 + i, low=95 + i, volume=1)
        for i in range(1, 21)
    ]
    support, resistance = support_resistance(bars, lookback=20)
    assert support == 96  # lowest low
    assert resistance == 125  # highest high
