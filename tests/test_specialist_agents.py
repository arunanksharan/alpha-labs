"""Integration tests for specialist quant research agents.

These tests run REAL computation against price data. They attempt to use
yfinance via ``fetch_and_prepare_prices``; if that fails (e.g. in CI without
network access), they fall back to synthetic OHLCV data injected via
monkeypatch.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import polars as pl
import pytest

from agents.specialists import AgentFinding
from agents.specialists.the_quant import TheQuant
from agents.specialists.the_technician import TheTechnician
from agents.specialists.the_contrarian import TheContrarian

# ---------------------------------------------------------------------------
# Synthetic OHLCV fallback
# ---------------------------------------------------------------------------

TICKER = "AAPL"
START = "2022-01-01"
END = "2024-12-31"


def _business_dates(start: date, n: int) -> list[date]:
    """Generate *n* weekday dates starting from *start*."""
    dates: list[date] = []
    current = start
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def _make_synthetic_ohlcv(ticker: str = TICKER, n: int = 750) -> pl.DataFrame:
    """Generate a synthetic OHLCV DataFrame that mirrors yfinance output."""
    rng = np.random.default_rng(42)
    dates = _business_dates(date(2022, 1, 3), n)

    log_returns = rng.normal(0.0003, 0.012, size=n)
    close = 150.0 * np.exp(np.cumsum(log_returns))
    noise = rng.uniform(0.001, 0.015, size=n)

    high = close * (1.0 + noise)
    low = close * (1.0 - noise)
    open_ = low + rng.uniform(0.0, 1.0, size=n) * (high - low)
    volume = rng.integers(500_000, 5_000_000, size=n).astype(np.float64)

    return pl.DataFrame(
        {
            "date": dates,
            "open": open_.tolist(),
            "high": high.tolist(),
            "low": low.tolist(),
            "close": close.tolist(),
            "volume": volume.tolist(),
        }
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def synthetic_prices() -> pl.DataFrame:
    return _make_synthetic_ohlcv()


@pytest.fixture(scope="module")
def _patch_fetch(synthetic_prices: pl.DataFrame) -> None:
    """Patch fetch_and_prepare_prices at module level if live data is unavailable."""
    # We try the real fetch once; if it works, we leave it alone.
    # If it fails, we patch for the rest of the test module.
    try:
        from core.adapters import fetch_and_prepare_prices
        fetch_and_prepare_prices(TICKER, START, END)
    except Exception:
        # Patch all three agent modules to use synthetic data
        import agents.specialists.the_quant as mod_quant
        import agents.specialists.the_technician as mod_tech
        import agents.specialists.the_contrarian as mod_contra

        def _fake_fetch(ticker: str, start: str, end: str) -> pl.DataFrame:
            return synthetic_prices

        mod_quant.fetch_and_prepare_prices = _fake_fetch  # type: ignore[attr-defined]
        mod_tech.fetch_and_prepare_prices = _fake_fetch  # type: ignore[attr-defined]
        mod_contra.fetch_and_prepare_prices = _fake_fetch  # type: ignore[attr-defined]


@pytest.fixture(scope="module")
def quant_finding(_patch_fetch: None) -> AgentFinding:
    return TheQuant().analyze(TICKER, START, END)


@pytest.fixture(scope="module")
def technician_finding(_patch_fetch: None) -> AgentFinding:
    return TheTechnician().analyze(TICKER, START, END)


@pytest.fixture(scope="module")
def contrarian_finding(_patch_fetch: None) -> AgentFinding:
    return TheContrarian().analyze(TICKER, START, END)


# ---------------------------------------------------------------------------
# TheQuant tests
# ---------------------------------------------------------------------------

class TestTheQuant:
    """Tests for TheQuant specialist agent."""

    def test_quant_returns_finding(self, quant_finding: AgentFinding) -> None:
        assert isinstance(quant_finding, AgentFinding)
        assert quant_finding.agent_name == "the_quant"
        assert quant_finding.ticker == TICKER

    def test_quant_has_thoughts(self, quant_finding: AgentFinding) -> None:
        assert isinstance(quant_finding.thoughts, list)
        assert len(quant_finding.thoughts) > 0
        # Should have at least the price fetch thought
        assert any("Fetched" in t for t in quant_finding.thoughts)

    def test_quant_signal_valid(self, quant_finding: AgentFinding) -> None:
        assert quant_finding.signal in ("bullish", "bearish", "neutral")

    def test_quant_confidence_bounded(self, quant_finding: AgentFinding) -> None:
        assert 0.0 <= quant_finding.confidence <= 1.0

    def test_quant_has_zscore(self, quant_finding: AgentFinding) -> None:
        assert "zscore" in quant_finding.details

    def test_quant_to_json(self, quant_finding: AgentFinding) -> None:
        payload = quant_finding.to_json()
        assert isinstance(payload, dict)
        assert set(payload.keys()) == {
            "agent_name", "ticker", "signal", "confidence",
            "reasoning", "details", "thoughts",
        }

    def test_quant_reasoning_not_empty(self, quant_finding: AgentFinding) -> None:
        assert isinstance(quant_finding.reasoning, str)
        assert len(quant_finding.reasoning) > 0


# ---------------------------------------------------------------------------
# TheTechnician tests
# ---------------------------------------------------------------------------

class TestTheTechnician:
    """Tests for TheTechnician specialist agent."""

    def test_technician_returns_finding(
        self, technician_finding: AgentFinding
    ) -> None:
        assert isinstance(technician_finding, AgentFinding)
        assert technician_finding.agent_name == "the_technician"
        assert technician_finding.ticker == TICKER

    def test_technician_has_thoughts(
        self, technician_finding: AgentFinding
    ) -> None:
        assert isinstance(technician_finding.thoughts, list)
        assert len(technician_finding.thoughts) > 0

    def test_technician_signal_valid(
        self, technician_finding: AgentFinding
    ) -> None:
        assert technician_finding.signal in ("bullish", "bearish", "neutral")

    def test_technician_confidence_bounded(
        self, technician_finding: AgentFinding
    ) -> None:
        assert 0.0 <= technician_finding.confidence <= 1.0

    def test_technician_has_indicator_details(
        self, technician_finding: AgentFinding
    ) -> None:
        """RSI and MACD must be present in details."""
        assert "rsi" in technician_finding.details
        assert "macd" in technician_finding.details

    def test_technician_has_bollinger(
        self, technician_finding: AgentFinding
    ) -> None:
        assert "bb_pct_b" in technician_finding.details

    def test_technician_has_atr(
        self, technician_finding: AgentFinding
    ) -> None:
        assert "atr" in technician_finding.details
        assert "atr_pct" in technician_finding.details

    def test_technician_to_json(
        self, technician_finding: AgentFinding
    ) -> None:
        payload = technician_finding.to_json()
        assert isinstance(payload, dict)
        assert payload["agent_name"] == "the_technician"


# ---------------------------------------------------------------------------
# TheContrarian tests
# ---------------------------------------------------------------------------

class TestTheContrarian:
    """Tests for TheContrarian specialist agent."""

    def test_contrarian_returns_finding(
        self, contrarian_finding: AgentFinding
    ) -> None:
        assert isinstance(contrarian_finding, AgentFinding)
        assert contrarian_finding.agent_name == "the_contrarian"
        assert contrarian_finding.ticker == TICKER

    def test_contrarian_has_thoughts(
        self, contrarian_finding: AgentFinding
    ) -> None:
        assert isinstance(contrarian_finding.thoughts, list)
        assert len(contrarian_finding.thoughts) > 0

    def test_contrarian_signal_valid(
        self, contrarian_finding: AgentFinding
    ) -> None:
        assert contrarian_finding.signal in ("bullish", "bearish", "neutral")

    def test_contrarian_confidence_bounded(
        self, contrarian_finding: AgentFinding
    ) -> None:
        assert 0.0 <= contrarian_finding.confidence <= 1.0

    def test_contrarian_has_stress_test(
        self, contrarian_finding: AgentFinding
    ) -> None:
        """Monte Carlo stress test results must be present."""
        assert "stress_test" in contrarian_finding.details
        st = contrarian_finding.details["stress_test"]
        assert "normal_var" in st
        assert "stressed_var" in st
        assert "stress_ratio" in st

    def test_contrarian_has_crowding(
        self, contrarian_finding: AgentFinding
    ) -> None:
        assert "crowding" in contrarian_finding.details
        assert contrarian_finding.details["crowding"] in (
            "neutral", "crowded_long", "crowded_short"
        )

    def test_contrarian_has_realized_vol(
        self, contrarian_finding: AgentFinding
    ) -> None:
        assert "realized_vol_pct" in contrarian_finding.details

    def test_contrarian_to_json(
        self, contrarian_finding: AgentFinding
    ) -> None:
        payload = contrarian_finding.to_json()
        assert isinstance(payload, dict)
        assert payload["agent_name"] == "the_contrarian"
