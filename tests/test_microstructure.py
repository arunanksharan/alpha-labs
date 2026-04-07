"""Tests for analytics.microstructure — execution benchmarks and liquidity."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from analytics.microstructure import (
    amihud_illiquidity,
    kyle_lambda,
    twap,
    vwap,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_ohlcv(n: int = 100, seed: int = 42) -> pl.DataFrame:
    """Generate a synthetic OHLCV DataFrame."""
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)
    volume = rng.integers(1000, 10000, size=n).astype(float)
    return pl.DataFrame(
        {
            "date": pl.date_range(
                pl.date(2024, 1, 1), pl.date(2024, 1, 1), eager=True
            ).extend_constant(pl.date(2024, 1, 1), n - 1)
            if False
            else [f"2024-01-{i + 1:02d}" for i in range(n)],
            "close": close.tolist(),
            "high": high.tolist(),
            "low": low.tolist(),
            "volume": volume.tolist(),
        }
    )


# ---------------------------------------------------------------------------
# VWAP
# ---------------------------------------------------------------------------

def test_vwap_adds_column() -> None:
    """vwap() should add a 'vwap' column to the frame."""
    df = _sample_ohlcv()
    result = vwap(df)
    assert "vwap" in result.columns
    assert len(result) == len(df)
    # First row VWAP should equal first row close (only one observation)
    assert result["vwap"][0] == pytest.approx(df["close"][0], rel=1e-8)


def test_vwap_weighted_correctly() -> None:
    """Manual check that VWAP = cumsum(price*vol) / cumsum(vol)."""
    df = pl.DataFrame(
        {
            "close": [10.0, 20.0, 30.0],
            "volume": [100.0, 200.0, 300.0],
        }
    )
    result = vwap(df)
    expected_last = (10 * 100 + 20 * 200 + 30 * 300) / (100 + 200 + 300)
    assert result["vwap"][-1] == pytest.approx(expected_last)


# ---------------------------------------------------------------------------
# TWAP
# ---------------------------------------------------------------------------

def test_twap_adds_column() -> None:
    """twap() should add a 'twap' column to the frame."""
    df = _sample_ohlcv()
    result = twap(df, window=5)
    assert "twap" in result.columns
    assert len(result) == len(df)


def test_twap_matches_rolling_mean() -> None:
    """TWAP with window=3 should match a simple rolling mean."""
    df = pl.DataFrame({"close": [1.0, 2.0, 3.0, 4.0, 5.0]})
    result = twap(df, window=3)
    # Window 3: [null, null, 2.0, 3.0, 4.0]
    assert result["twap"][2] == pytest.approx(2.0)
    assert result["twap"][4] == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# Amihud illiquidity
# ---------------------------------------------------------------------------

def test_amihud_positive() -> None:
    """Amihud ratio should be non-negative where defined."""
    df = _sample_ohlcv(n=100)
    result = amihud_illiquidity(df, window=10)
    assert "amihud" in result.columns
    # After the warm-up period, values should be positive
    non_null = result.filter(pl.col("amihud").is_not_null())
    assert (non_null["amihud"] >= 0).all()


def test_amihud_higher_for_illiquid() -> None:
    """A stock with less volume should have a higher Amihud ratio."""
    rng = np.random.default_rng(99)
    n = 60
    close = (100 + np.cumsum(rng.normal(0, 0.5, n))).tolist()
    liquid = pl.DataFrame({"close": close, "volume": [10000.0] * n})
    illiquid = pl.DataFrame({"close": close, "volume": [100.0] * n})
    a_liq = amihud_illiquidity(liquid, window=10)["amihud"][-1]
    a_illiq = amihud_illiquidity(illiquid, window=10)["amihud"][-1]
    assert a_illiq > a_liq


# ---------------------------------------------------------------------------
# Kyle's lambda
# ---------------------------------------------------------------------------

def test_kyle_lambda_positive_for_trending() -> None:
    """For a price series trending up with positive volume, lambda > 0."""
    n = 200
    close = np.linspace(100, 120, n) + np.random.default_rng(7).normal(0, 0.1, n)
    volume = np.full(n, 1000.0)
    df = pl.DataFrame({"close": close.tolist(), "volume": volume.tolist()})
    lam = kyle_lambda(df)
    assert lam > 0
