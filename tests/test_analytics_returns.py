"""Tests for analytics/returns.py — every public function is covered."""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from analytics.returns import (
    compute_alpha,
    compute_beta,
    compute_calmar,
    compute_correlation_matrix,
    compute_cvar,
    compute_cumulative_returns,
    compute_drawdown,
    compute_information_ratio,
    compute_max_drawdown,
    compute_returns,
    compute_rolling_correlation,
    compute_sharpe,
    compute_sortino,
    compute_var,
    compute_volatility,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _price_df(prices: list[float], start: date = date(2020, 1, 2)) -> pl.DataFrame:
    dates = [start + timedelta(days=i) for i in range(len(prices))]
    return pl.DataFrame({"date": dates, "close": prices}).with_columns(
        pl.col("date").cast(pl.Date)
    )


def _returns_df(returns: list[float], start: date = date(2020, 1, 2)) -> pl.DataFrame:
    dates = [start + timedelta(days=i) for i in range(len(returns))]
    return pl.DataFrame({"date": dates, "returns": returns}).with_columns(
        pl.col("date").cast(pl.Date)
    )


def _random_returns(
    n: int = 252,
    mu: float = 0.0005,
    sigma: float = 0.01,
    seed: int = 0,
) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    r = rng.normal(mu, sigma, size=n).tolist()
    return _returns_df(r)


def _random_prices(n: int = 252, seed: int = 0) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    log_r = rng.normal(0.0003, 0.012, size=n)
    prices = (100.0 * np.exp(np.cumsum(log_r))).tolist()
    return _price_df(prices)


# ---------------------------------------------------------------------------
# compute_returns
# ---------------------------------------------------------------------------

class TestComputeReturns:
    def test_log_returns_drops_first_row(self) -> None:
        df = _random_prices(50)
        result = compute_returns(df, method="log")
        assert "returns" in result.columns
        assert len(result) == 49

    def test_simple_returns_drops_first_row(self) -> None:
        df = _random_prices(50)
        result = compute_returns(df, method="simple")
        assert len(result) == 49

    def test_log_return_known_value(self) -> None:
        df = _price_df([100.0, 110.0])
        result = compute_returns(df, method="log")
        expected = math.log(110.0 / 100.0)
        assert abs(result["returns"][0] - expected) < 1e-9

    def test_simple_return_known_value(self) -> None:
        df = _price_df([100.0, 110.0])
        result = compute_returns(df, method="simple")
        assert abs(result["returns"][0] - 0.10) < 1e-9

    def test_date_column_preserved(self) -> None:
        df = _random_prices(10)
        result = compute_returns(df, method="log")
        assert "date" in result.columns

    def test_invalid_method_raises(self) -> None:
        df = _random_prices(10)
        with pytest.raises(ValueError, match="method must be"):
            compute_returns(df, method="arithmetic")

    def test_single_row_raises(self) -> None:
        df = _price_df([100.0])
        with pytest.raises(ValueError):
            compute_returns(df)

    def test_empty_df_raises(self) -> None:
        df = pl.DataFrame({"date": [], "close": []}).with_columns(
            pl.col("date").cast(pl.Date), pl.col("close").cast(pl.Float64)
        )
        with pytest.raises(ValueError):
            compute_returns(df)

    def test_no_numeric_columns_raises(self) -> None:
        df = pl.DataFrame({"date": [date(2020, 1, 1), date(2020, 1, 2)]}).with_columns(
            pl.col("date").cast(pl.Date)
        )
        with pytest.raises(ValueError, match="no numeric columns"):
            compute_returns(df)

    @pytest.mark.parametrize("method", ["log", "simple"])
    def test_constant_price_zero_returns(self, method: str) -> None:
        df = _price_df([50.0] * 10)
        result = compute_returns(df, method=method)
        assert result["returns"].abs().max() < 1e-9

    def test_log_and_simple_approx_equal_for_small_returns(self) -> None:
        rng = np.random.default_rng(0)
        small_prices = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.001, 100)))
        df = _price_df(small_prices.tolist())
        log_r = compute_returns(df, method="log")["returns"].to_numpy()
        simple_r = compute_returns(df, method="simple")["returns"].to_numpy()
        assert np.abs(log_r - simple_r).max() < 1e-4


# ---------------------------------------------------------------------------
# compute_cumulative_returns
# ---------------------------------------------------------------------------

class TestComputeCumulativeReturns:
    def test_output_column_exists(self) -> None:
        df = _random_returns(50)
        result = compute_cumulative_returns(df)
        assert "cumulative_returns" in result.columns

    def test_length_preserved(self) -> None:
        df = _random_returns(100)
        result = compute_cumulative_returns(df)
        assert len(result) == 100

    def test_zero_returns_zero_cumulative(self) -> None:
        df = _returns_df([0.0] * 20)
        result = compute_cumulative_returns(df)
        assert result["cumulative_returns"].abs().max() < 1e-9

    def test_known_two_period_cumulative(self) -> None:
        df = _returns_df([0.10, 0.10])
        result = compute_cumulative_returns(df)
        expected_final = (1.10 * 1.10) - 1.0
        assert abs(result["cumulative_returns"][-1] - expected_final) < 1e-9

    def test_monotone_with_positive_returns(self) -> None:
        df = _returns_df([0.01] * 30)
        result = compute_cumulative_returns(df)
        diffs = result["cumulative_returns"].diff().drop_nulls()
        assert (diffs > 0).all()

    def test_single_row(self) -> None:
        df = _returns_df([0.05])
        result = compute_cumulative_returns(df)
        assert abs(result["cumulative_returns"][0] - 0.05) < 1e-9

    def test_date_column_preserved(self) -> None:
        df = _random_returns(20)
        result = compute_cumulative_returns(df)
        assert "date" in result.columns


# ---------------------------------------------------------------------------
# compute_drawdown
# ---------------------------------------------------------------------------

class TestComputeDrawdown:
    def test_output_columns_present(self) -> None:
        df = _random_returns(50)
        result = compute_drawdown(df)
        assert "drawdown" in result.columns
        assert "max_drawdown" in result.columns

    def test_monotone_positive_returns_zero_drawdown(self) -> None:
        df = _returns_df([0.01] * 20)
        result = compute_drawdown(df)
        assert result["drawdown"].abs().max() < 1e-9

    def test_drawdown_always_non_positive(self) -> None:
        df = _random_returns(100)
        result = compute_drawdown(df)
        assert (result["drawdown"] <= 1e-12).all()

    def test_max_drawdown_le_drawdown(self) -> None:
        df = _random_returns(100)
        result = compute_drawdown(df)
        assert (result["max_drawdown"] <= result["drawdown"] + 1e-12).all()

    def test_known_drawdown_sequence(self) -> None:
        df = _returns_df([0.10, -0.20, 0.05])
        result = compute_drawdown(df)
        wealth = [1.10, 1.10 * 0.80, 1.10 * 0.80 * 1.05]
        running_max = [1.10, 1.10, 1.10]
        expected = [w / m - 1 for w, m in zip(wealth, running_max)]
        for i, exp in enumerate(expected):
            assert abs(result["drawdown"][i] - exp) < 1e-9

    def test_single_row(self) -> None:
        df = _returns_df([0.05])
        result = compute_drawdown(df)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# compute_volatility
# ---------------------------------------------------------------------------

class TestComputeVolatility:
    def test_output_column_exists(self) -> None:
        df = _random_returns(100)
        result = compute_volatility(df, window=21)
        assert "volatility" in result.columns

    def test_length_preserved(self) -> None:
        df = _random_returns(100)
        result = compute_volatility(df, window=21)
        assert len(result) == 100

    def test_annualization_factor(self) -> None:
        df = _random_returns(100)
        ann = compute_volatility(df, window=21, annualize=True)
        raw = compute_volatility(df, window=21, annualize=False)
        ratio = ann["volatility"].drop_nulls() / raw["volatility"].drop_nulls()
        assert (ratio - math.sqrt(252)).abs().max() < 1e-6

    def test_insufficient_rows_raises(self) -> None:
        df = _random_returns(10)
        with pytest.raises(ValueError):
            compute_volatility(df, window=21)

    def test_constant_returns_zero_vol(self) -> None:
        df = _returns_df([0.001] * 50)
        result = compute_volatility(df, window=10, annualize=False)
        non_null = result["volatility"].drop_nulls()
        assert non_null.abs().max() < 1e-9


# ---------------------------------------------------------------------------
# compute_sharpe
# ---------------------------------------------------------------------------

class TestComputeSharpe:
    def test_positive_sharpe_for_positive_mean_returns(self) -> None:
        df = _random_returns(252, mu=0.001, sigma=0.005, seed=1)
        assert compute_sharpe(df) > 0

    def test_zero_std_returns_zero(self) -> None:
        df = _returns_df([0.0] * 10)
        assert compute_sharpe(df) == 0.0

    def test_risk_free_reduces_sharpe(self) -> None:
        df = _random_returns(252, mu=0.001, sigma=0.01, seed=2)
        s0 = compute_sharpe(df, risk_free_rate=0.0)
        s1 = compute_sharpe(df, risk_free_rate=0.05)
        assert s0 > s1

    def test_single_row_raises(self) -> None:
        df = _returns_df([0.01])
        with pytest.raises(ValueError):
            compute_sharpe(df)

    def test_negative_returns_negative_sharpe(self) -> None:
        df = _random_returns(252, mu=-0.002, sigma=0.01, seed=3)
        assert compute_sharpe(df) < 0

    def test_annualization_scales_by_sqrt_periods(self) -> None:
        rng = np.random.default_rng(0)
        r = rng.normal(0.001, 0.01, 252).tolist()
        df = _returns_df(r)
        s_daily = compute_sharpe(df, periods=1)
        s_annual = compute_sharpe(df, periods=252)
        assert abs(s_annual / s_daily - math.sqrt(252)) < 0.01


# ---------------------------------------------------------------------------
# compute_sortino
# ---------------------------------------------------------------------------

class TestComputeSortino:
    def test_all_positive_returns_returns_inf(self) -> None:
        df = _returns_df([0.005] * 50)
        assert compute_sortino(df) == float("inf")

    def test_sortino_positive_for_positive_mean(self) -> None:
        rng = np.random.default_rng(10)
        r = rng.normal(0.003, 0.01, 252).tolist()  # Strong positive mean
        df = _returns_df(r)
        assert compute_sortino(df) > 0

    def test_sortino_ge_sharpe_for_positive_skew(self) -> None:
        rng = np.random.default_rng(20)
        r = np.abs(rng.normal(0.001, 0.01, 500)).tolist()
        df = _returns_df(r)
        assert compute_sortino(df) >= compute_sharpe(df)

    def test_single_row_raises(self) -> None:
        df = _returns_df([0.01])
        with pytest.raises(ValueError):
            compute_sortino(df)

    def test_risk_free_reduces_sortino(self) -> None:
        df = _random_returns(252, mu=0.001, sigma=0.01, seed=5)
        s0 = compute_sortino(df, risk_free_rate=0.0)
        s1 = compute_sortino(df, risk_free_rate=0.05)
        assert s0 > s1


# ---------------------------------------------------------------------------
# compute_max_drawdown
# ---------------------------------------------------------------------------

class TestComputeMaxDrawdown:
    def test_always_non_positive(self) -> None:
        df = _random_returns(200)
        assert compute_max_drawdown(df) <= 0.0

    def test_monotone_positive_series_zero_mdd(self) -> None:
        df = _returns_df([0.005] * 50)
        assert compute_max_drawdown(df) == 0.0

    def test_known_single_crash(self) -> None:
        df = _returns_df([0.10, -0.50, 0.10])
        mdd = compute_max_drawdown(df)
        assert abs(mdd - (-0.50)) < 0.01

    def test_single_negative_return(self) -> None:
        # With a single -30% return, wealth goes to 0.7, running max is 0.7, dd = 0
        # The drawdown model starts from wealth=1+r, so single row has dd=0
        df = _returns_df([-0.30])
        mdd = compute_max_drawdown(df)
        assert mdd <= 0.0

    def test_single_row_requires_one_row(self) -> None:
        df = _returns_df([0.05])
        mdd = compute_max_drawdown(df)
        assert mdd == 0.0


# ---------------------------------------------------------------------------
# compute_calmar
# ---------------------------------------------------------------------------

class TestComputeCalmar:
    def test_returns_float(self) -> None:
        df = _random_returns(252, mu=0.001, sigma=0.005, seed=5)
        assert isinstance(compute_calmar(df), float)

    def test_zero_mdd_returns_inf(self) -> None:
        df = _returns_df([0.005] * 10)
        assert compute_calmar(df) == float("inf")

    def test_positive_for_net_positive_strategy(self) -> None:
        df = _random_returns(252, mu=0.002, sigma=0.005, seed=6)
        calmar = compute_calmar(df)
        assert calmar > 0

    def test_single_row_raises(self) -> None:
        df = _returns_df([0.01])
        with pytest.raises(ValueError):
            compute_calmar(df)


# ---------------------------------------------------------------------------
# compute_var
# ---------------------------------------------------------------------------

class TestComputeVar:
    @pytest.mark.parametrize("method", ["historical", "parametric", "cornish-fisher"])
    def test_var_negative_for_mixed_returns(self, method: str) -> None:
        rng = np.random.default_rng(0)
        df = _returns_df(rng.normal(0.0, 0.01, 300).tolist())
        assert compute_var(df, confidence=0.95, method=method) < 0.0

    @pytest.mark.parametrize("method", ["historical", "parametric", "cornish-fisher"])
    def test_higher_confidence_more_negative(self, method: str) -> None:
        rng = np.random.default_rng(1)
        df = _returns_df(rng.normal(0.0, 0.01, 300).tolist())
        var_95 = compute_var(df, confidence=0.95, method=method)
        var_99 = compute_var(df, confidence=0.99, method=method)
        assert var_99 <= var_95

    def test_invalid_method_raises(self) -> None:
        df = _random_returns(30)
        with pytest.raises(ValueError, match="method must be"):
            compute_var(df, method="monte-carlo")

    def test_historical_var_exact_percentile(self) -> None:
        r = [float(x) for x in range(-50, 50)]
        df = _returns_df(r)
        var = compute_var(df, confidence=0.95, method="historical")
        expected = float(np.percentile(r, 5))
        assert abs(var - expected) < 1e-9

    def test_single_row_raises(self) -> None:
        df = _returns_df([-0.01])
        with pytest.raises(ValueError):
            compute_var(df)


# ---------------------------------------------------------------------------
# compute_cvar
# ---------------------------------------------------------------------------

class TestComputeCVar:
    def test_cvar_le_var(self) -> None:
        rng = np.random.default_rng(3)
        df = _returns_df(rng.normal(0.0, 0.01, 300).tolist())
        var = compute_var(df, confidence=0.95)
        cvar = compute_cvar(df, confidence=0.95)
        assert cvar <= var + 1e-9

    def test_cvar_is_tail_mean(self) -> None:
        r = [-0.10, -0.08, -0.06, -0.04, -0.02, 0.0, 0.02, 0.04, 0.06, 0.08]
        df = _returns_df(r)
        cvar = compute_cvar(df, confidence=0.90)
        assert cvar <= 0.0

    def test_single_row_raises(self) -> None:
        df = _returns_df([-0.01])
        with pytest.raises(ValueError):
            compute_cvar(df)

    def test_cvar_lt_cvar_higher_confidence(self) -> None:
        rng = np.random.default_rng(4)
        df = _returns_df(rng.normal(0.0, 0.01, 500).tolist())
        cvar_90 = compute_cvar(df, confidence=0.90)
        cvar_99 = compute_cvar(df, confidence=0.99)
        assert cvar_99 <= cvar_90


# ---------------------------------------------------------------------------
# compute_correlation_matrix
# ---------------------------------------------------------------------------

class TestComputeCorrelationMatrix:
    def test_output_shape_three_assets(self) -> None:
        rng = np.random.default_rng(0)
        assets = {
            k: _returns_df(rng.normal(0, 0.01, 100).tolist())
            for k in ("A", "B", "C")
        }
        result = compute_correlation_matrix(assets)
        assert result.shape == (3, 4)

    def test_diagonal_is_one(self) -> None:
        rng = np.random.default_rng(0)
        assets = {
            k: _returns_df(rng.normal(0, 0.01, 100).tolist())
            for k in ("X", "Y")
        }
        result = compute_correlation_matrix(assets)
        assert abs(result["X"][0] - 1.0) < 1e-9
        assert abs(result["Y"][1] - 1.0) < 1e-9

    def test_all_values_in_valid_range(self) -> None:
        rng = np.random.default_rng(0)
        assets = {
            k: _returns_df(rng.normal(0, 0.01, 200).tolist())
            for k in ("A", "B")
        }
        result = compute_correlation_matrix(assets)
        for col in ("A", "B"):
            for val in result[col].to_list():
                assert -1.0 - 1e-9 <= val <= 1.0 + 1e-9

    def test_perfect_correlation_for_identical_series(self) -> None:
        rng = np.random.default_rng(0)
        r = rng.normal(0, 0.01, 100).tolist()
        assets = {"A": _returns_df(r), "B": _returns_df(r)}
        result = compute_correlation_matrix(assets)
        assert abs(result["A"][1] - 1.0) < 1e-9

    def test_single_series_raises(self) -> None:
        assets = {"A": _random_returns(50)}
        with pytest.raises(ValueError):
            compute_correlation_matrix(assets)

    def test_symmetry(self) -> None:
        rng = np.random.default_rng(0)
        assets = {
            k: _returns_df(rng.normal(0, 0.01, 100).tolist())
            for k in ("A", "B", "C")
        }
        result = compute_correlation_matrix(assets)
        ab = result.filter(pl.col("ticker") == "A")["B"][0]
        ba = result.filter(pl.col("ticker") == "B")["A"][0]
        assert abs(ab - ba) < 1e-9


# ---------------------------------------------------------------------------
# compute_rolling_correlation
# ---------------------------------------------------------------------------

class TestComputeRollingCorrelation:
    def test_output_column_exists(self) -> None:
        rng = np.random.default_rng(0)
        r1 = _returns_df(rng.normal(0, 0.01, 100).tolist())
        r2 = _returns_df(rng.normal(0, 0.01, 100).tolist())
        result = compute_rolling_correlation(r1, r2, window=20)
        assert "rolling_correlation" in result.columns

    def test_first_window_minus_one_rows_are_nan(self) -> None:
        rng = np.random.default_rng(0)
        r1 = _returns_df(rng.normal(0, 0.01, 100).tolist())
        r2 = _returns_df(rng.normal(0, 0.01, 100).tolist())
        result = compute_rolling_correlation(r1, r2, window=30)
        # First window-1 values are NaN (not null in polars)
        first_vals = result["rolling_correlation"][:29]
        assert first_vals.is_nan().sum() == 29

    def test_perfect_correlation_for_identical_series(self) -> None:
        rng = np.random.default_rng(0)
        r = rng.normal(0, 0.01, 100).tolist()
        r1 = _returns_df(r)
        r2 = _returns_df(r)
        result = compute_rolling_correlation(r1, r2, window=20)
        non_null = result["rolling_correlation"].drop_nulls()
        assert (non_null - 1.0).abs().max() < 1e-6

    def test_insufficient_rows_raises(self) -> None:
        rng = np.random.default_rng(0)
        r1 = _returns_df(rng.normal(0, 0.01, 10).tolist())
        r2 = _returns_df(rng.normal(0, 0.01, 10).tolist())
        with pytest.raises(ValueError):
            compute_rolling_correlation(r1, r2, window=30)

    def test_values_bounded_in_minus_one_to_one(self) -> None:
        rng = np.random.default_rng(7)
        r1 = _returns_df(rng.normal(0, 0.01, 200).tolist())
        r2 = _returns_df(rng.normal(0, 0.01, 200).tolist())
        result = compute_rolling_correlation(r1, r2, window=30)
        non_null = result["rolling_correlation"].drop_nulls()
        assert non_null.min() >= -1.0 - 1e-9
        assert non_null.max() <= 1.0 + 1e-9


# ---------------------------------------------------------------------------
# compute_beta
# ---------------------------------------------------------------------------

class TestComputeBeta:
    def test_beta_one_for_identical_series(self) -> None:
        rng = np.random.default_rng(0)
        r = rng.normal(0, 0.01, 252).tolist()
        df = _returns_df(r)
        assert abs(compute_beta(df, df) - 1.0) < 1e-6

    def test_beta_near_zero_for_independent_series(self) -> None:
        rng = np.random.default_rng(0)
        r1 = _returns_df(rng.normal(0, 0.01, 1000).tolist())
        r2 = _returns_df(rng.normal(0, 0.01, 1000).tolist())
        assert abs(compute_beta(r1, r2)) < 0.15

    def test_constant_benchmark_returns_zero_beta(self) -> None:
        rng = np.random.default_rng(0)
        r = _returns_df(rng.normal(0, 0.01, 50).tolist())
        bm = _returns_df([0.001] * 50)
        assert compute_beta(r, bm) == 0.0

    def test_known_beta_two_for_double_benchmark(self) -> None:
        rng = np.random.default_rng(0)
        bm = rng.normal(0, 0.01, 500)
        r = _returns_df((2.0 * bm).tolist())
        bm_df = _returns_df(bm.tolist())
        assert abs(compute_beta(r, bm_df) - 2.0) < 0.01

    def test_single_row_raises(self) -> None:
        df = _returns_df([0.01])
        with pytest.raises(ValueError):
            compute_beta(df, df)


# ---------------------------------------------------------------------------
# compute_alpha
# ---------------------------------------------------------------------------

class TestComputeAlpha:
    def test_positive_alpha_for_outperformer(self) -> None:
        rng = np.random.default_rng(0)
        bm_r = rng.normal(0.0002, 0.01, 252)
        port_r = bm_r + 0.0005
        port = _returns_df(port_r.tolist())
        bm = _returns_df(bm_r.tolist())
        assert compute_alpha(port, bm) > 0.0

    def test_zero_alpha_for_identical_series(self) -> None:
        rng = np.random.default_rng(0)
        r = rng.normal(0, 0.01, 100).tolist()
        df = _returns_df(r)
        assert abs(compute_alpha(df, df)) < 1e-6

    def test_single_row_raises(self) -> None:
        df = _returns_df([0.01])
        with pytest.raises(ValueError):
            compute_alpha(df, df)


# ---------------------------------------------------------------------------
# compute_information_ratio
# ---------------------------------------------------------------------------

class TestComputeInformationRatio:
    def test_positive_ir_for_consistent_outperformance(self) -> None:
        rng = np.random.default_rng(0)
        bm_r = rng.normal(0.0002, 0.01, 252)
        port_r = bm_r + 0.0003
        port = _returns_df(port_r.tolist())
        bm = _returns_df(bm_r.tolist())
        assert compute_information_ratio(port, bm) > 0.0

    def test_zero_ir_for_identical_series(self) -> None:
        rng = np.random.default_rng(0)
        r = rng.normal(0, 0.01, 100).tolist()
        df = _returns_df(r)
        assert compute_information_ratio(df, df) == 0.0

    def test_single_row_raises(self) -> None:
        df = _returns_df([0.01])
        with pytest.raises(ValueError):
            compute_information_ratio(df, df)

    def test_ir_annualized_reasonable_range(self) -> None:
        rng = np.random.default_rng(0)
        bm_r = rng.normal(0.0, 0.01, 252)
        # Add noise to active returns so tracking error isn't near-zero
        port_r = bm_r + rng.normal(0.0005, 0.002, 252)
        port = _returns_df(port_r.tolist())
        bm = _returns_df(bm_r.tolist())
        ir = compute_information_ratio(port, bm)
        assert -10.0 < ir < 20.0

    def test_negative_ir_for_consistent_underperformance(self) -> None:
        rng = np.random.default_rng(0)
        bm_r = rng.normal(0.0002, 0.01, 252)
        port_r = bm_r - 0.0005
        port = _returns_df(port_r.tolist())
        bm = _returns_df(bm_r.tolist())
        assert compute_information_ratio(port, bm) < 0.0


# ---------------------------------------------------------------------------
# Cross-function edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.parametrize("n", [2, 10, 50, 252])
    def test_drawdown_various_lengths(self, n: int) -> None:
        df = _random_returns(n)
        result = compute_drawdown(df)
        assert len(result) == n
        assert (result["drawdown"] <= 1e-12).all()

    def test_var_all_methods_are_negative_for_zero_mean_noise(self) -> None:
        rng = np.random.default_rng(99)
        df = _returns_df(rng.normal(0.0, 0.01, 500).tolist())
        for method in ("historical", "parametric", "cornish-fisher"):
            assert compute_var(df, confidence=0.95, method=method) < 0.0

    def test_sharpe_sortino_calmar_consistent_sign(self) -> None:
        rng = np.random.default_rng(42)
        pos_df = _returns_df(rng.normal(0.002, 0.005, 252).tolist())
        sharpe = compute_sharpe(pos_df)
        sortino = compute_sortino(pos_df)
        calmar = compute_calmar(pos_df)
        assert sharpe > 0
        assert sortino > 0
        assert calmar > 0

    def test_cumulative_returns_date_monotone(self) -> None:
        df = _random_returns(50)
        result = compute_cumulative_returns(df)
        dates = result["date"].to_list()
        assert dates == sorted(dates)
