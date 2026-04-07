"""Tests for execution algorithms (VWAP/TWAP scheduling, IS, paper trading)."""

from __future__ import annotations

import math

import numpy as np
import polars as pl
import pytest

from core.strategies import Signal
from execution.algorithms.paper_trader import PaperTrader
from execution.algorithms.vwap_twap import (
    ExecutionPlan,
    implementation_shortfall,
    optimal_execution_horizon,
    twap_schedule,
    vwap_schedule,
)


# ---------------------------------------------------------------------------
# Helpers -- synthetic data factories
# ---------------------------------------------------------------------------


def _make_historical_volumes(n_slots: int = 10) -> pl.DataFrame:
    """Create a synthetic intraday volume profile with a U-shape."""
    slots = list(range(n_slots))
    # U-shaped volume: high at open/close, low mid-day
    x = np.linspace(-1, 1, n_slots)
    volumes = (1.0 + x**2) * 1_000.0
    return pl.DataFrame(
        {
            "time_slot": slots,
            "avg_volume": volumes.tolist(),
        }
    )


def _make_execution_prices(n_slices: int = 5, base_price: float = 100.0) -> pl.DataFrame:
    """Create synthetic execution prices with slight upward drift."""
    return pl.DataFrame(
        {
            "time_slot": list(range(n_slices)),
            "price": [base_price + i * 0.05 for i in range(n_slices)],
            "quantity": [200.0] * n_slices,
        }
    )


# ===================================================================
# VWAP tests
# ===================================================================


class TestVWAPSchedule:
    """Tests for vwap_schedule."""

    def test_vwap_schedule_proportional_to_volume(self) -> None:
        """Target quantities should be proportional to slot volumes."""
        volumes = _make_historical_volumes(n_slots=5)
        plan = vwap_schedule(total_quantity=10_000.0, historical_volumes=volumes, n_slices=5)

        vol_arr = volumes.get_column("avg_volume").to_numpy()
        expected_pcts = vol_arr / vol_arr.sum()

        actual_pcts = plan.schedule.get_column("target_pct").to_numpy()
        np.testing.assert_allclose(actual_pcts, expected_pcts, atol=1e-10)

    def test_vwap_total_quantity_matches(self) -> None:
        """Sum of per-slot quantities must equal the total order size."""
        volumes = _make_historical_volumes(n_slots=10)
        plan = vwap_schedule(total_quantity=5_000.0, historical_volumes=volumes, n_slices=10)

        total_scheduled = plan.schedule.get_column("target_quantity").sum()
        assert total_scheduled == pytest.approx(5_000.0, rel=1e-9)

    def test_vwap_zero_quantity(self) -> None:
        """Zero quantity should produce an empty schedule."""
        volumes = _make_historical_volumes()
        plan = vwap_schedule(total_quantity=0.0, historical_volumes=volumes)
        assert plan.schedule.height == 0
        assert plan.estimated_cost_bps == 0.0

    def test_vwap_returns_execution_plan(self) -> None:
        """Return type must be ExecutionPlan with correct algorithm label."""
        volumes = _make_historical_volumes()
        plan = vwap_schedule(total_quantity=1_000.0, historical_volumes=volumes)
        assert isinstance(plan, ExecutionPlan)
        assert plan.algorithm == "VWAP"


# ===================================================================
# TWAP tests
# ===================================================================


class TestTWAPSchedule:
    """Tests for twap_schedule."""

    def test_twap_equal_distribution(self) -> None:
        """All time slots should receive the same quantity."""
        plan = twap_schedule(total_quantity=10_000.0, n_slices=5)

        quantities = plan.schedule.get_column("target_quantity").to_numpy()
        np.testing.assert_allclose(quantities, 2_000.0, atol=1e-10)

    def test_twap_total_quantity_matches(self) -> None:
        """Sum of per-slot quantities must equal the total order."""
        plan = twap_schedule(total_quantity=7_777.0, n_slices=13)
        total = plan.schedule.get_column("target_quantity").sum()
        assert total == pytest.approx(7_777.0, rel=1e-9)

    def test_twap_percentages_sum_to_one(self) -> None:
        """Target percentages must sum to 1."""
        plan = twap_schedule(total_quantity=1_000.0, n_slices=8)
        pct_sum = plan.schedule.get_column("target_pct").sum()
        assert pct_sum == pytest.approx(1.0, rel=1e-9)

    def test_twap_invalid_slices_raises(self) -> None:
        """Zero or negative n_slices should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            twap_schedule(total_quantity=1_000.0, n_slices=0)


# ===================================================================
# Implementation shortfall tests
# ===================================================================


class TestImplementationShortfall:
    """Tests for implementation_shortfall."""

    def test_implementation_shortfall_calculation(self) -> None:
        """Total IS should match (VWAP_exec - target) / target in bps."""
        target = 100.0
        exec_df = _make_execution_prices(n_slices=5, base_price=100.0)

        result = implementation_shortfall(target_price=target, execution_prices=exec_df)

        # Executed VWAP = mean(100.0, 100.05, 100.10, 100.15, 100.20) = 100.10
        expected_is_bps = (100.10 - 100.0) / 100.0 * 10_000.0
        assert result["total_is_bps"] == pytest.approx(expected_is_bps, rel=1e-3)

    def test_implementation_shortfall_components_sum(self) -> None:
        """Delay + impact + timing must equal total IS."""
        exec_df = _make_execution_prices(n_slices=4, base_price=50.0)
        result = implementation_shortfall(target_price=49.95, execution_prices=exec_df)

        component_sum = result["delay_bps"] + result["impact_bps"] + result["timing_bps"]
        assert component_sum == pytest.approx(result["total_is_bps"], abs=1e-3)

    def test_implementation_shortfall_empty(self) -> None:
        """Empty execution prices should return all zeros."""
        empty = pl.DataFrame(
            {
                "time_slot": pl.Series([], dtype=pl.Int64),
                "price": pl.Series([], dtype=pl.Float64),
                "quantity": pl.Series([], dtype=pl.Float64),
            }
        )
        result = implementation_shortfall(target_price=100.0, execution_prices=empty)
        assert result["total_is_bps"] == 0.0


# ===================================================================
# Optimal execution horizon tests
# ===================================================================


class TestOptimalHorizon:
    """Tests for optimal_execution_horizon."""

    def test_optimal_horizon_increases_with_size(self) -> None:
        """Larger orders should need a longer execution horizon."""
        t_small = optimal_execution_horizon(
            total_quantity=1_000.0,
            daily_volume=1_000_000.0,
            volatility=0.02,
        )
        t_large = optimal_execution_horizon(
            total_quantity=100_000.0,
            daily_volume=1_000_000.0,
            volatility=0.02,
        )
        assert t_large > t_small

    def test_optimal_horizon_urgency_shortens(self) -> None:
        """Higher urgency should produce a shorter horizon."""
        t_normal = optimal_execution_horizon(
            total_quantity=10_000.0,
            daily_volume=500_000.0,
            volatility=0.02,
            urgency=1.0,
        )
        t_urgent = optimal_execution_horizon(
            total_quantity=10_000.0,
            daily_volume=500_000.0,
            volatility=0.02,
            urgency=2.0,
        )
        assert t_urgent < t_normal

    def test_optimal_horizon_zero_quantity(self) -> None:
        """Zero quantity should return 0 trading days."""
        t = optimal_execution_horizon(
            total_quantity=0.0,
            daily_volume=1_000_000.0,
            volatility=0.02,
        )
        assert t == 0.0


# ===================================================================
# Paper trader tests
# ===================================================================


class TestPaperTrader:
    """Tests for PaperTrader."""

    def test_paper_trader_initial_state(self) -> None:
        """A fresh trader should have full cash and no positions."""
        trader = PaperTrader(initial_capital=50_000.0)
        assert trader.portfolio.cash == 50_000.0
        assert trader.portfolio.positions == {}
        assert trader.portfolio.history == []

    def test_paper_trader_buy_reduces_cash(self) -> None:
        """Executing a buy signal should reduce available cash."""
        trader = PaperTrader(initial_capital=100_000.0)
        signals = [
            Signal(
                ticker="AAPL",
                date="2025-01-15",
                direction=1.0,
                confidence=1.0,
            ),
        ]
        prices = {"AAPL": 150.0}
        trader.execute_signals(signals, prices)

        # direction=1.0, confidence=1.0 -> 100 shares @ 150 = 15_000
        assert trader.portfolio.cash == pytest.approx(100_000.0 - 15_000.0)
        assert trader.portfolio.positions["AAPL"] == pytest.approx(100.0)

    def test_paper_trader_portfolio_value(self) -> None:
        """Portfolio value should equal cash + position market value."""
        trader = PaperTrader(initial_capital=100_000.0)
        signals = [
            Signal(ticker="MSFT", date="2025-01-15", direction=1.0, confidence=0.5),
        ]
        prices = {"MSFT": 400.0}
        trader.execute_signals(signals, prices)

        # 50 shares @ 400 = 20_000 cost; cash = 80_000; value = 80_000 + 50*400 = 100_000
        value = trader.get_portfolio_value(prices)
        assert value == pytest.approx(100_000.0)

    def test_paper_trader_performance_tracks_history(self) -> None:
        """Performance DataFrame should grow with each execute_signals call."""
        trader = PaperTrader(initial_capital=100_000.0)

        for i in range(3):
            signals = [
                Signal(
                    ticker="GOOG",
                    date=f"2025-01-{15 + i:02d}",
                    direction=1.0,
                    confidence=0.1,
                ),
            ]
            prices = {"GOOG": 170.0 + i}
            trader.execute_signals(signals, prices)

        perf = trader.get_performance()
        assert perf.height == 3
        assert set(perf.columns) == {
            "date",
            "portfolio_value",
            "daily_return",
            "cumulative_return",
        }

    def test_paper_trader_reset(self) -> None:
        """Reset should restore initial capital and clear positions."""
        trader = PaperTrader(initial_capital=50_000.0)
        signals = [
            Signal(ticker="TSLA", date="2025-01-15", direction=1.0, confidence=1.0),
        ]
        trader.execute_signals(signals, {"TSLA": 250.0})
        assert trader.portfolio.positions != {}

        trader.reset()
        assert trader.portfolio.cash == 50_000.0
        assert trader.portfolio.positions == {}
        assert trader.portfolio.history == []

    def test_paper_trader_sell_increases_cash(self) -> None:
        """A sell signal should add cash (short sell)."""
        trader = PaperTrader(initial_capital=100_000.0)
        signals = [
            Signal(ticker="META", date="2025-01-15", direction=-1.0, confidence=1.0),
        ]
        prices = {"META": 500.0}
        trader.execute_signals(signals, prices)

        # -100 shares @ 500 -> cash += 50_000
        assert trader.portfolio.cash == pytest.approx(150_000.0)
        assert trader.portfolio.positions["META"] == pytest.approx(-100.0)
