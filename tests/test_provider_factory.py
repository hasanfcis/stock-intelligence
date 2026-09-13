import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stock_intel.provider_factory import build_providers
from stock_intel.providers.mock import MockMacroDataProvider, MockMarketDataProvider, MockNewsProvider


def test_non_live_always_returns_mocks():
    market_data, news, sentiment_fn, macro_data = build_providers(live=False)
    assert isinstance(market_data, MockMarketDataProvider)
    assert isinstance(news, MockNewsProvider)
    assert isinstance(macro_data, MockMacroDataProvider)
    assert sentiment_fn is None


def test_live_falls_back_to_mocks_when_env_vars_and_packages_missing(monkeypatch):
    """With no ALPACA/FINNHUB/ANTHROPIC/FRED keys set and (in this test env)
    the live-only packages not installed, --live must not crash — it should
    log a warning and fall back to mocks for each missing piece."""
    for var in [
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "FINNHUB_API_KEY",
        "ANTHROPIC_API_KEY",
        "FRED_API_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)

    market_data, news, sentiment_fn, macro_data = build_providers(live=True)

    assert isinstance(market_data, MockMarketDataProvider)
    assert isinstance(news, MockNewsProvider)
    assert isinstance(macro_data, MockMacroDataProvider)
    assert sentiment_fn is None
