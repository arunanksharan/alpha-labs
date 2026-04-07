"""Tests for analytics.options — Black-Scholes pricing, Greeks, and volatility."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from analytics.options import (
    OptionPrice,
    black_scholes,
    garch_forecast,
    implied_volatility,
)


# ---------------------------------------------------------------------------
# Black-Scholes pricing
# ---------------------------------------------------------------------------

def test_bs_call_known_value() -> None:
    """ATM call with standard parameters should match the textbook value."""
    result = black_scholes(S=100, K=100, T=1, r=0.05, sigma=0.2, option_type="call")
    assert isinstance(result, OptionPrice)
    # Textbook value ~10.4506
    assert result.price == pytest.approx(10.4506, abs=0.01)


def test_bs_put_call_parity() -> None:
    """Put-call parity: C - P = S - K * exp(-rT)."""
    S, K, T, r, sigma = 100.0, 105.0, 0.5, 0.05, 0.25
    call = black_scholes(S, K, T, r, sigma, option_type="call")
    put = black_scholes(S, K, T, r, sigma, option_type="put")
    parity_rhs = S - K * np.exp(-r * T)
    assert (call.price - put.price) == pytest.approx(parity_rhs, abs=1e-8)


# ---------------------------------------------------------------------------
# Greeks bounds
# ---------------------------------------------------------------------------

def test_delta_bounds() -> None:
    """Call delta in [0, 1]; put delta in [-1, 0]."""
    for K in [80, 100, 120]:
        call = black_scholes(100, K, 1, 0.05, 0.2, "call")
        put = black_scholes(100, K, 1, 0.05, 0.2, "put")
        assert 0.0 <= call.delta <= 1.0, f"Call delta out of range for K={K}"
        assert -1.0 <= put.delta <= 0.0, f"Put delta out of range for K={K}"


def test_gamma_positive() -> None:
    """Gamma is always positive for vanilla options."""
    for K in [80, 100, 120]:
        call = black_scholes(100, K, 1, 0.05, 0.2, "call")
        put = black_scholes(100, K, 1, 0.05, 0.2, "put")
        assert call.gamma > 0
        assert put.gamma > 0
        # Gamma should be the same for call and put
        assert call.gamma == pytest.approx(put.gamma, abs=1e-10)


def test_vega_positive() -> None:
    """Vega is always positive for vanilla options."""
    for K in [80, 100, 120]:
        call = black_scholes(100, K, 1, 0.05, 0.2, "call")
        put = black_scholes(100, K, 1, 0.05, 0.2, "put")
        assert call.vega > 0
        assert put.vega > 0
        # Vega should be the same for call and put
        assert call.vega == pytest.approx(put.vega, abs=1e-10)


# ---------------------------------------------------------------------------
# Implied volatility
# ---------------------------------------------------------------------------

def test_implied_vol_recovers_input() -> None:
    """IV solver should recover the volatility used to generate the price."""
    sigma_input = 0.3
    S, K, T, r = 100.0, 100.0, 1.0, 0.05
    price = black_scholes(S, K, T, r, sigma_input, "call").price
    iv = implied_volatility(price, S, K, T, r, "call")
    assert iv == pytest.approx(sigma_input, abs=1e-5)


def test_implied_vol_put() -> None:
    """IV solver should also work for puts."""
    sigma_input = 0.25
    S, K, T, r = 110.0, 100.0, 0.5, 0.03
    price = black_scholes(S, K, T, r, sigma_input, "put").price
    iv = implied_volatility(price, S, K, T, r, "put")
    assert iv == pytest.approx(sigma_input, abs=1e-5)


# ---------------------------------------------------------------------------
# GARCH forecast
# ---------------------------------------------------------------------------

def test_garch_forecast_shape() -> None:
    """GARCH forecast should return the requested number of rows."""
    rng = np.random.default_rng(42)
    returns = pl.Series("returns", rng.normal(0, 0.01, 500))
    horizon = 10
    result = garch_forecast(returns, p=1, q=1, horizon=horizon)
    assert isinstance(result, pl.DataFrame)
    assert len(result) == horizon
    assert set(result.columns) >= {"step", "forecast_vol", "lower_ci", "upper_ci"}
    # All volatility forecasts should be positive
    assert (result["forecast_vol"] > 0).all()
