"""Tests for Monte Carlo VaR simulation."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from risk.var.monte_carlo import MonteCarloVaR


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mc() -> MonteCarloVaR:
    return MonteCarloVaR(n_simulations=50_000, seed=42)


@pytest.fixture()
def historical_returns() -> pl.Series:
    """Synthetic daily returns resembling a typical equity."""
    rng = np.random.default_rng(7)
    r = rng.normal(0.0004, 0.012, size=500)
    return pl.Series("returns", r)


@pytest.fixture()
def uncorrelated_returns() -> dict[str, pl.Series]:
    """Two independently-generated return series."""
    rng_a = np.random.default_rng(10)
    rng_b = np.random.default_rng(20)
    n = 500
    return {
        "A": pl.Series("A", rng_a.normal(0.0004, 0.012, size=n)),
        "B": pl.Series("B", rng_b.normal(0.0003, 0.010, size=n)),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSimulateReturns:
    def test_simulate_returns_shape(
        self, mc: MonteCarloVaR, historical_returns: pl.Series
    ) -> None:
        n_days = 5
        result = mc.simulate_returns(historical_returns, n_days=n_days)
        assert result.shape == (mc.n_simulations, n_days)

    def test_simulate_returns_single_day_shape(
        self, mc: MonteCarloVaR, historical_returns: pl.Series
    ) -> None:
        result = mc.simulate_returns(historical_returns, n_days=1)
        assert result.shape == (mc.n_simulations, 1)


class TestComputeVaR:
    def test_var_negative_for_typical_returns(
        self, mc: MonteCarloVaR, historical_returns: pl.Series
    ) -> None:
        var = mc.compute_var(historical_returns, confidence=0.95)
        assert var < 0.0, "95% VaR should be negative for typical equity returns"

    def test_var_higher_confidence_more_negative(
        self, historical_returns: pl.Series
    ) -> None:
        mc = MonteCarloVaR(n_simulations=50_000, seed=99)
        var_95 = mc.compute_var(historical_returns, confidence=0.95)

        mc2 = MonteCarloVaR(n_simulations=50_000, seed=99)
        var_99 = mc2.compute_var(historical_returns, confidence=0.99)

        assert var_99 < var_95, "99% VaR should be more negative than 95% VaR"

    def test_multi_day_var_more_negative(
        self, historical_returns: pl.Series
    ) -> None:
        mc1 = MonteCarloVaR(n_simulations=50_000, seed=123)
        var_1d = mc1.compute_var(historical_returns, confidence=0.95, n_days=1)

        mc2 = MonteCarloVaR(n_simulations=50_000, seed=123)
        var_10d = mc2.compute_var(historical_returns, confidence=0.95, n_days=10)

        assert var_10d < var_1d, (
            "10-day VaR should be more negative than 1-day VaR"
        )


class TestComputeCVaR:
    def test_cvar_worse_than_var(
        self, historical_returns: pl.Series
    ) -> None:
        mc1 = MonteCarloVaR(n_simulations=50_000, seed=55)
        var = mc1.compute_var(historical_returns, confidence=0.95)

        mc2 = MonteCarloVaR(n_simulations=50_000, seed=55)
        cvar = mc2.compute_cvar(historical_returns, confidence=0.95)

        assert cvar <= var, "CVaR (expected shortfall) must be <= VaR"


class TestPortfolioVaR:
    def test_portfolio_var_diversification(
        self, uncorrelated_returns: dict[str, pl.Series]
    ) -> None:
        weights = {"A": 0.5, "B": 0.5}

        # Portfolio VaR (correlated simulation)
        mc_p = MonteCarloVaR(n_simulations=50_000, seed=42)
        portfolio = mc_p.portfolio_var(uncorrelated_returns, weights, confidence=0.95)

        # Sum of individual weighted VaRs (no diversification benefit)
        mc_a = MonteCarloVaR(n_simulations=50_000, seed=42)
        var_a = mc_a.compute_var(uncorrelated_returns["A"], confidence=0.95)

        mc_b = MonteCarloVaR(n_simulations=50_000, seed=42)
        var_b = mc_b.compute_var(uncorrelated_returns["B"], confidence=0.95)

        undiversified = 0.5 * var_a + 0.5 * var_b

        # Diversified portfolio VaR should be less negative (better) than
        # the simple weighted sum of individual VaRs.
        assert portfolio > undiversified, (
            "Diversified portfolio VaR should be less negative than the "
            "sum of weighted individual VaRs for uncorrelated assets"
        )


class TestStressTest:
    def test_stress_test_increases_var(
        self, historical_returns: pl.Series
    ) -> None:
        mc = MonteCarloVaR(n_simulations=50_000, seed=42)
        result = mc.stress_test(historical_returns, shock_multiplier=2.0)

        assert "normal_var" in result
        assert "stressed_var" in result
        assert "stress_ratio" in result

        assert result["stressed_var"] < result["normal_var"], (
            "Stressed VaR should be more negative than normal VaR"
        )


class TestReproducibility:
    def test_seed_reproducibility(self, historical_returns: pl.Series) -> None:
        mc1 = MonteCarloVaR(n_simulations=10_000, seed=77)
        var1 = mc1.compute_var(historical_returns, confidence=0.95)

        mc2 = MonteCarloVaR(n_simulations=10_000, seed=77)
        var2 = mc2.compute_var(historical_returns, confidence=0.95)

        assert var1 == var2, "Same seed must produce identical results"
