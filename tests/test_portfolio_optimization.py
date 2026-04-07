"""Tests for the portfolio optimisation engine.

Uses synthetic multi-asset returns with known correlation structure
to verify optimiser correctness.
"""

from __future__ import annotations

import json

import numpy as np
import polars as pl
import pytest

from portfolio.optimization.optimizer import PortfolioOptimizer, PortfolioResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def synthetic_returns() -> pl.DataFrame:
    """Generate 500-day synthetic returns for 4 correlated assets.

    Correlation structure:
        Asset_A and Asset_B are positively correlated (~0.6).
        Asset_C is weakly correlated with A/B.
        Asset_D is negatively correlated with A (~-0.3).

    Asset_A has the highest expected return; Asset_D has the lowest
    volatility.
    """
    rng = np.random.default_rng(42)
    n_days = 500

    # Target correlation matrix
    corr = np.array([
        [1.00, 0.60, 0.10, -0.30],
        [0.60, 1.00, 0.20, -0.10],
        [0.10, 0.20, 1.00,  0.05],
        [-0.30, -0.10, 0.05, 1.00],
    ])

    # Target annualised vols  (daily = ann / sqrt(252))
    ann_vols = np.array([0.20, 0.25, 0.15, 0.10])
    daily_vols = ann_vols / np.sqrt(252)

    # Build covariance matrix
    D = np.diag(daily_vols)
    daily_cov = D @ corr @ D

    # Cholesky decomposition for correlated sampling
    L = np.linalg.cholesky(daily_cov)

    # Daily means (annualised: 12%, 10%, 8%, 4%)
    ann_means = np.array([0.12, 0.10, 0.08, 0.04])
    daily_means = ann_means / 252

    z = rng.standard_normal((n_days, 4))
    returns_mat = z @ L.T + daily_means

    return pl.DataFrame({
        "Asset_A": returns_mat[:, 0],
        "Asset_B": returns_mat[:, 1],
        "Asset_C": returns_mat[:, 2],
        "Asset_D": returns_mat[:, 3],
    })


@pytest.fixture()
def optimizer() -> PortfolioOptimizer:
    return PortfolioOptimizer()


# ---------------------------------------------------------------------------
# Mean-variance tests
# ---------------------------------------------------------------------------

class TestMeanVariance:
    def test_weights_sum_to_one(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        result = optimizer.mean_variance(synthetic_returns)
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-6, f"Weights sum to {total}, expected 1.0"

    def test_all_positive_weights(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        """Long-only constraint: all weights >= 0."""
        result = optimizer.mean_variance(synthetic_returns)
        for asset, w in result.weights.items():
            assert w >= -1e-8, f"{asset} has negative weight {w}"

    def test_result_fields(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        result = optimizer.mean_variance(synthetic_returns)
        assert result.method == "mean_variance"
        assert result.expected_vol > 0
        assert isinstance(result.sharpe_ratio, float)

    def test_target_return(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        """When a feasible target_return is set, expected_return should match."""
        # Use a target within the feasible range of sample means
        cols = [
            c for c in synthetic_returns.columns
            if synthetic_returns[c].dtype in (pl.Float32, pl.Float64)
        ]
        mat = synthetic_returns.select(cols).to_numpy()
        ann_means = mat.mean(axis=0) * 252
        # Pick a target in the middle of the feasible range
        target = float((ann_means.min() + ann_means.max()) / 2)
        result = optimizer.mean_variance(synthetic_returns, target_return=target)
        assert abs(result.expected_return - target) < 0.02, (
            f"Expected ~{target:.4f}, got {result.expected_return:.4f}"
        )


# ---------------------------------------------------------------------------
# Minimum variance tests
# ---------------------------------------------------------------------------

class TestMinVariance:
    def test_lower_vol_than_equal_weight(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        """Min-variance portfolio should have lower vol than 1/N."""
        result = optimizer.min_variance(synthetic_returns)
        # Compute equal-weight portfolio vol for comparison
        cols = [
            c for c in synthetic_returns.columns
            if synthetic_returns[c].dtype in (pl.Float32, pl.Float64)
        ]
        mat = synthetic_returns.select(cols).to_numpy()
        cov = np.cov(mat, rowvar=False) * 252
        n = len(cols)
        w_eq = np.ones(n) / n
        eq_vol = float(np.sqrt(w_eq @ cov @ w_eq))

        assert result.expected_vol < eq_vol, (
            f"Min-var vol {result.expected_vol:.4f} >= equal-weight vol {eq_vol:.4f}"
        )


# ---------------------------------------------------------------------------
# Hierarchical Risk Parity tests
# ---------------------------------------------------------------------------

class TestHRP:
    def test_weights_sum_to_one(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        result = optimizer.hierarchical_risk_parity(synthetic_returns)
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-6, f"HRP weights sum to {total}"

    def test_all_positive_weights(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        result = optimizer.hierarchical_risk_parity(synthetic_returns)
        for asset, w in result.weights.items():
            assert w >= -1e-8, f"{asset} has negative HRP weight {w}"

    def test_returns_portfolio_result(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        result = optimizer.hierarchical_risk_parity(synthetic_returns)
        assert isinstance(result, PortfolioResult)
        assert result.method == "hierarchical_risk_parity"


# ---------------------------------------------------------------------------
# Black-Litterman tests
# ---------------------------------------------------------------------------

class TestBlackLitterman:
    def test_incorporates_views(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        """A strong bullish view on Asset_D should increase its weight
        relative to the equilibrium (market-cap) allocation."""
        market_caps = {
            "Asset_A": 500.0,
            "Asset_B": 300.0,
            "Asset_C": 150.0,
            "Asset_D": 50.0,
        }

        # Without views: equilibrium weights favour Asset_A (largest cap)
        result_no_views = optimizer.black_litterman(
            synthetic_returns,
            market_caps=market_caps,
            views=[],
        )

        # With strong bullish view on Asset_D
        views = [
            {"assets": ["Asset_D"], "returns": 0.30, "confidence": 0.9},
        ]
        result_with_views = optimizer.black_litterman(
            synthetic_returns,
            market_caps=market_caps,
            views=views,
        )

        assert result_with_views.weights["Asset_D"] > result_no_views.weights["Asset_D"], (
            f"View did not increase Asset_D weight: "
            f"no-view={result_no_views.weights['Asset_D']:.4f}, "
            f"with-view={result_with_views.weights['Asset_D']:.4f}"
        )

    def test_weights_sum_to_one(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        market_caps = {"Asset_A": 500, "Asset_B": 300, "Asset_C": 150, "Asset_D": 50}
        views = [{"assets": ["Asset_A"], "returns": 0.15, "confidence": 0.7}]
        result = optimizer.black_litterman(
            synthetic_returns, market_caps=market_caps, views=views,
        )
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Risk parity tests
# ---------------------------------------------------------------------------

class TestRiskParity:
    def test_equal_risk_contribution(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        """Risk contributions should be approximately equal across assets."""
        result = optimizer.risk_parity(synthetic_returns)

        cols = [
            c for c in synthetic_returns.columns
            if synthetic_returns[c].dtype in (pl.Float32, pl.Float64)
        ]
        mat = synthetic_returns.select(cols).to_numpy()
        cov = np.cov(mat, rowvar=False) * 252

        w = np.array([result.weights[c] for c in cols])
        port_vol = float(np.sqrt(w @ cov @ w))

        # Marginal risk contributions: w_i * (Sigma @ w)_i / port_vol
        marginal = cov @ w
        risk_contrib = w * marginal / port_vol
        # Normalise to percentages
        rc_pct = risk_contrib / risk_contrib.sum()

        # With 4 assets, each should contribute ~25% +/- 10%
        expected = 1.0 / len(cols)
        for i, c in enumerate(cols):
            assert abs(rc_pct[i] - expected) < 0.10, (
                f"{c} risk contribution {rc_pct[i]:.3f} deviates from "
                f"expected {expected:.3f}"
            )

    def test_weights_sum_to_one(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        result = optimizer.risk_parity(synthetic_returns)
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Efficient frontier tests
# ---------------------------------------------------------------------------

class TestEfficientFrontier:
    def test_shape(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        frontier = optimizer.efficient_frontier(synthetic_returns, n_points=20)
        assert isinstance(frontier, pl.DataFrame)
        # Should have at least some feasible portfolios
        assert len(frontier) >= 5
        expected_cols = {
            "target_return", "expected_return", "expected_vol",
            "sharpe_ratio", "weights_json",
        }
        assert expected_cols == set(frontier.columns)

    def test_return_increases(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        """Expected returns should be non-decreasing along the frontier."""
        frontier = optimizer.efficient_frontier(synthetic_returns, n_points=30)
        rets = frontier["expected_return"].to_list()
        for i in range(1, len(rets)):
            # Allow small tolerance for solver noise
            assert rets[i] >= rets[i - 1] - 1e-4, (
                f"Return decreased at point {i}: {rets[i-1]:.6f} -> {rets[i]:.6f}"
            )

    def test_weights_json_parseable(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        frontier = optimizer.efficient_frontier(synthetic_returns, n_points=10)
        for row in frontier.iter_rows(named=True):
            weights = json.loads(row["weights_json"])
            assert isinstance(weights, dict)
            assert abs(sum(weights.values()) - 1.0) < 1e-4


# ---------------------------------------------------------------------------
# Regime-aware tests
# ---------------------------------------------------------------------------

class TestRegimeAware:
    def test_returns_result(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        result = optimizer.regime_aware(synthetic_returns)
        assert isinstance(result, PortfolioResult)
        assert result.method == "regime_aware"
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-6
        assert result.expected_vol > 0

    def test_all_positive_weights(
        self,
        optimizer: PortfolioOptimizer,
        synthetic_returns: pl.DataFrame,
    ) -> None:
        result = optimizer.regime_aware(synthetic_returns)
        for asset, w in result.weights.items():
            assert w >= -1e-8, f"{asset} has negative regime-aware weight {w}"
