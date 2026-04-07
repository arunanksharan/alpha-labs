"""Tests for strategies/combiner.py — StrategyCombiner."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from core.strategies import Signal
from strategies.combiner import StrategyCombiner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _business_dates(start: date, n: int) -> list[date]:
    dates: list[date] = []
    current = start
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def _returns_df(
    n: int = 252, mean: float = 0.0004, std: float = 0.01, seed: int = 42
) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    dates = _business_dates(date(2022, 1, 3), n)
    return pl.DataFrame(
        {"date": dates, "returns": rng.normal(mean, std, n).tolist()}
    ).with_columns(pl.col("date").cast(pl.Date))


def _make_signals(
    ticker: str, dt: str, direction: float, confidence: float
) -> Signal:
    return Signal(ticker=ticker, date=dt, direction=direction, confidence=confidence)


# ---------------------------------------------------------------------------
# combine
# ---------------------------------------------------------------------------


class TestCombine:
    def test_equal_weight_combine(self) -> None:
        """Two strategies with equal weight produce averaged directions."""
        combiner = StrategyCombiner()  # None = equal weight
        strat_a = [_make_signals("AAPL", "2022-01-03", 1.0, 0.8)]
        strat_b = [_make_signals("MSFT", "2022-01-03", -1.0, 0.7)]

        result = combiner.combine({"a": strat_a, "b": strat_b})
        assert len(result) == 2

        by_ticker = {s.ticker: s for s in result}
        # Each signal only from one strategy, so direction = original * weight
        # weight = 0.5 for equal
        assert abs(by_ticker["AAPL"].direction - 1.0 * 0.5) < 1e-10
        assert abs(by_ticker["MSFT"].direction - (-1.0) * 0.5) < 1e-10

    def test_weighted_combine(self) -> None:
        """One strategy weighted more heavily."""
        combiner = StrategyCombiner(weights={"a": 0.8, "b": 0.2})
        strat_a = [_make_signals("AAPL", "2022-01-03", 1.0, 0.8)]
        strat_b = [_make_signals("MSFT", "2022-01-03", -1.0, 0.6)]

        result = combiner.combine({"a": strat_a, "b": strat_b})
        by_ticker = {s.ticker: s for s in result}

        # AAPL only in strat_a -> direction = 1.0 * (0.8/1.0) = 0.8
        assert abs(by_ticker["AAPL"].direction - 0.8) < 1e-10
        # MSFT only in strat_b -> direction = -1.0 * (0.2/1.0) = -0.2
        assert abs(by_ticker["MSFT"].direction - (-0.2)) < 1e-10

    def test_same_ticker_same_date_merged(self) -> None:
        """Same (date, ticker) from two strategies gets merged."""
        combiner = StrategyCombiner(weights={"a": 0.6, "b": 0.4})
        strat_a = [_make_signals("AAPL", "2022-01-03", 1.0, 0.8)]
        strat_b = [_make_signals("AAPL", "2022-01-03", -0.5, 0.9)]

        result = combiner.combine({"a": strat_a, "b": strat_b})
        assert len(result) == 1

        sig = result[0]
        # Weighted average direction: (0.6*1.0 + 0.4*(-0.5)) / (0.6+0.4) = 0.4
        expected_direction = (0.6 * 1.0 + 0.4 * (-0.5)) / (0.6 + 0.4)
        assert abs(sig.direction - expected_direction) < 1e-10
        # Max confidence
        assert sig.confidence == 0.9


# ---------------------------------------------------------------------------
# correlation_analysis
# ---------------------------------------------------------------------------


class TestCorrelationAnalysis:
    def test_correlation_analysis_returns_matrix(self) -> None:
        combiner = StrategyCombiner()
        returns = {
            "strat_a": _returns_df(seed=1),
            "strat_b": _returns_df(seed=2),
            "strat_c": _returns_df(seed=3),
        }
        corr = combiner.correlation_analysis(returns)

        assert "ticker" in corr.columns
        assert "strat_a" in corr.columns
        assert "strat_b" in corr.columns
        assert "strat_c" in corr.columns
        assert len(corr) == 3

        # Diagonal should be 1.0
        for name in ["strat_a", "strat_b", "strat_c"]:
            row = corr.filter(pl.col("ticker") == name)
            assert abs(row[name][0] - 1.0) < 1e-10


# ---------------------------------------------------------------------------
# optimal_weights
# ---------------------------------------------------------------------------


class TestOptimalWeights:
    def test_optimal_weights_equal(self) -> None:
        combiner = StrategyCombiner()
        returns = {
            "a": _returns_df(seed=10),
            "b": _returns_df(seed=20),
            "c": _returns_df(seed=30),
        }
        weights = combiner.optimal_weights(returns, method="equal")

        assert set(weights.keys()) == {"a", "b", "c"}
        assert abs(sum(weights.values()) - 1.0) < 1e-10
        for v in weights.values():
            assert abs(v - 1.0 / 3) < 1e-10

    def test_optimal_weights_inverse_vol(self) -> None:
        combiner = StrategyCombiner()
        # Strategy with lower vol should get higher weight
        low_vol = _returns_df(std=0.005, seed=10)
        high_vol = _returns_df(std=0.020, seed=20)
        returns = {"low_vol": low_vol, "high_vol": high_vol}

        weights = combiner.optimal_weights(returns, method="inverse_vol")

        assert abs(sum(weights.values()) - 1.0) < 1e-10
        assert weights["low_vol"] > weights["high_vol"]

    def test_optimal_weights_sharpe_weighted(self) -> None:
        combiner = StrategyCombiner()
        # Good strategy: very high positive mean relative to vol
        good = _returns_df(mean=0.005, std=0.005, seed=10)
        # Bad strategy: strongly negative mean
        bad = _returns_df(mean=-0.005, std=0.005, seed=20)

        returns = {"good": good, "bad": bad}
        weights = combiner.optimal_weights(returns, method="sharpe_weighted")

        assert abs(sum(weights.values()) - 1.0) < 1e-10
        # Bad strategy should get 0 weight (negative Sharpe)
        assert weights["bad"] == 0.0
        assert weights["good"] > 0.0

    def test_optimal_weights_invalid_method(self) -> None:
        combiner = StrategyCombiner()
        with pytest.raises(ValueError, match="method must be"):
            combiner.optimal_weights({"a": _returns_df()}, method="magic")


# ---------------------------------------------------------------------------
# performance_summary
# ---------------------------------------------------------------------------


class TestPerformanceSummary:
    def test_performance_summary_schema(self) -> None:
        combiner = StrategyCombiner()
        returns = {
            "strat_a": _returns_df(seed=1),
            "strat_b": _returns_df(seed=2),
        }
        summary = combiner.performance_summary(returns)

        assert "strategy" in summary.columns
        assert "sharpe" in summary.columns
        assert "sortino" in summary.columns
        assert "max_drawdown" in summary.columns
        assert "ann_return" in summary.columns
        assert len(summary) == 2

        strategies = summary["strategy"].to_list()
        assert "strat_a" in strategies
        assert "strat_b" in strategies
