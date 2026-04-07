"""Tests for execution cost modelling."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from backtest.execution_model import ExecutionCost, ExecutionModel


# ---------------------------------------------------------------------------
# Cost computation
# ---------------------------------------------------------------------------


class TestComputeCosts:
    def test_compute_costs_all_positive(self) -> None:
        model = ExecutionModel()
        cost = model.compute_costs(trade_value=100_000.0)

        assert cost.commission > 0
        assert cost.slippage > 0
        assert cost.market_impact > 0
        assert cost.total == pytest.approx(
            cost.commission + cost.slippage + cost.market_impact
        )

    def test_market_impact_increases_with_size(self) -> None:
        """Larger trades should incur more market impact."""
        model = ExecutionModel()
        small = model.compute_costs(trade_value=10_000.0)
        large = model.compute_costs(trade_value=1_000_000.0)

        assert large.market_impact > small.market_impact

    def test_commission_proportional_to_value(self) -> None:
        model = ExecutionModel(commission_bps=10.0)
        cost_1 = model.compute_costs(trade_value=100_000.0)
        cost_2 = model.compute_costs(trade_value=200_000.0)

        assert cost_2.commission == pytest.approx(2.0 * cost_1.commission)

    def test_zero_trade_zero_cost(self) -> None:
        model = ExecutionModel()
        cost = model.compute_costs(trade_value=0.0)

        assert cost.commission == 0.0
        assert cost.slippage == 0.0
        assert cost.market_impact == 0.0
        assert cost.total == 0.0


# ---------------------------------------------------------------------------
# Turnover
# ---------------------------------------------------------------------------


class TestTurnover:
    def test_turnover_detects_weight_changes(self) -> None:
        weights = pl.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "AAPL": [0.5, 0.3, 0.4],
                "GOOG": [0.5, 0.7, 0.6],
            }
        )
        result = ExecutionModel.compute_turnover(weights)

        assert "turnover" in result.columns
        assert result.height == 3
        # First row is 0 (no prior), second row: |0.3-0.5| + |0.7-0.5| = 0.4
        turnover = result.get_column("turnover").to_list()
        assert turnover[0] == pytest.approx(0.0)
        assert turnover[1] == pytest.approx(0.4)
        assert turnover[2] == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# Capacity estimate
# ---------------------------------------------------------------------------


class TestCapacity:
    def test_capacity_estimate_positive(self) -> None:
        """A profitable strategy should have positive capacity."""
        rng = np.random.default_rng(42)
        n = 252
        daily_ret = 0.001 + rng.normal(0, 0.01, n)

        strategy_returns = pl.DataFrame({"date": list(range(n)), "returns": daily_ret})
        volumes = pl.DataFrame({"date": list(range(n)), "volume": [1e8] * n})

        model = ExecutionModel()
        cap = model.capacity_estimate(strategy_returns, volumes)

        assert cap > 0
        assert np.isfinite(cap)
