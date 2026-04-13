"""Tests for analytics/structural_breaks.py.

Synthetic series with KNOWN statistical properties are used so assertions
are grounded in the data-generating process rather than arbitrary thresholds.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from analytics.structural_breaks import StructuralBreakDetector


# ---------------------------------------------------------------------------
# Synthetic data factories
# ---------------------------------------------------------------------------


def _mean_shift_data(
    n: int = 200, shift: float = 5.0, seed: int = 0
) -> tuple[np.ndarray, np.ndarray, int]:
    """First half mean=0, second half mean=shift. Returns (y, x, breakpoint)."""
    rng = np.random.default_rng(seed)
    bp = n // 2
    y1 = rng.normal(0.0, 1.0, bp)
    y2 = rng.normal(shift, 1.0, n - bp)
    y = np.concatenate([y1, y2])
    x = np.column_stack([np.ones(n)])  # intercept only
    return y, x, bp


def _homogeneous_data(
    n: int = 200, seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """Homogeneous normal data with intercept regressor."""
    rng = np.random.default_rng(seed)
    y = rng.normal(0.0, 1.0, n)
    x = np.column_stack([np.ones(n)])
    return y, x


def _bubble_prices(n: int = 200, seed: int = 0) -> pl.DataFrame:
    """Simulate exponential bubble: random walk then explosive growth."""
    rng = np.random.default_rng(seed)
    # First 60% random walk, last 40% explosive
    n_rw = int(n * 0.6)
    n_exp = n - n_rw
    rw = 100.0 + np.cumsum(rng.normal(0.0, 0.5, n_rw))
    # Explosive: compound at ~2% per step with noise
    last_price = rw[-1]
    exp_prices = [last_price]
    for _ in range(n_exp - 1):
        exp_prices.append(exp_prices[-1] * (1.02 + rng.normal(0.0, 0.005)))
    prices = np.concatenate([rw, np.array(exp_prices)])
    return pl.DataFrame({
        "date": list(range(len(prices))),
        "close": prices,
    })


def _random_walk_prices(n: int = 300, seed: int = 0) -> pl.DataFrame:
    """Pure random walk (no drift, no explosiveness)."""
    rng = np.random.default_rng(seed)
    prices = 100.0 + np.cumsum(rng.normal(0.0, 1.0, n))
    # Ensure all positive
    prices = prices - prices.min() + 10.0
    return pl.DataFrame({
        "date": list(range(n)),
        "close": prices,
    })


def _slope_change_data(
    n: int = 300, window: int = 60, seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """Regression with slope change at midpoint.

    First half: y = 1.0 * x + noise
    Second half: y = 5.0 * x + noise
    """
    rng = np.random.default_rng(seed)
    bp = n // 2
    t = np.arange(n, dtype=np.float64) / n
    noise = rng.normal(0.0, 0.5, n)
    y = np.where(np.arange(n) < bp, 1.0 * t, 5.0 * t) + noise
    x = np.column_stack([t, np.ones(n)])
    return y, x


def _stationary_regression_data(
    n: int = 300, seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """Stable linear relationship with no coefficient change."""
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=np.float64) / n
    noise = rng.normal(0.0, 0.3, n)
    y = 2.0 * t + 1.0 + noise
    x = np.column_stack([t, np.ones(n)])
    return y, x


def _mean_reverting_prices(n: int = 300, seed: int = 0) -> pl.DataFrame:
    """Ornstein-Uhlenbeck process (mean-reverting around 100)."""
    rng = np.random.default_rng(seed)
    prices = np.zeros(n)
    prices[0] = 100.0
    theta = 0.3
    mu = 100.0
    for t in range(1, n):
        prices[t] = prices[t - 1] + theta * (mu - prices[t - 1]) + rng.normal(0.0, 1.0)
    return pl.DataFrame({
        "date": list(range(n)),
        "close": prices,
    })


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def detector() -> StructuralBreakDetector:
    return StructuralBreakDetector()


# ---------------------------------------------------------------------------
# Chow test
# ---------------------------------------------------------------------------


class TestChowTest:
    """Test 1-2: Chow test detects known mean shifts."""

    def test_detects_mean_shift(self, detector: StructuralBreakDetector) -> None:
        """Chow test identifies structural break at known mean shift."""
        y, x, bp = _mean_shift_data(n=200, shift=5.0, seed=0)
        result = detector.chow_test(y, x, breakpoint=bp)

        assert "f_stat" in result
        assert "p_value" in result
        assert "is_break" in result
        assert result["is_break"] is True
        assert result["p_value"] < 0.01  # strong rejection

    def test_no_break_for_homogeneous_data(
        self, detector: StructuralBreakDetector
    ) -> None:
        """Chow test does not reject null for homogeneous data."""
        y, x = _homogeneous_data(n=200, seed=0)
        result = detector.chow_test(y, x, breakpoint=100)

        assert result["is_break"] is False
        assert result["p_value"] > 0.05

    def test_returns_required_keys(
        self, detector: StructuralBreakDetector
    ) -> None:
        y, x, bp = _mean_shift_data()
        result = detector.chow_test(y, x, bp)
        assert {"f_stat", "p_value", "is_break"} <= result.keys()

    def test_f_stat_positive(self, detector: StructuralBreakDetector) -> None:
        y, x, bp = _mean_shift_data()
        result = detector.chow_test(y, x, bp)
        assert result["f_stat"] > 0

    def test_p_value_bounded(self, detector: StructuralBreakDetector) -> None:
        y, x, bp = _mean_shift_data()
        result = detector.chow_test(y, x, bp)
        assert 0.0 <= result["p_value"] <= 1.0

    def test_invalid_breakpoint_raises(
        self, detector: StructuralBreakDetector
    ) -> None:
        y, x = _homogeneous_data(n=100)
        with pytest.raises(ValueError, match="Breakpoint"):
            detector.chow_test(y, x, breakpoint=0)
        with pytest.raises(ValueError, match="Breakpoint"):
            detector.chow_test(y, x, breakpoint=99)

    def test_1d_x_is_reshaped(self, detector: StructuralBreakDetector) -> None:
        """Passing x as 1D should work (auto-reshape)."""
        rng = np.random.default_rng(0)
        x = np.ones(100)
        y = np.concatenate([rng.normal(0, 1, 50), rng.normal(5, 1, 50)])
        result = detector.chow_test(y, x, breakpoint=50)
        assert result["is_break"] is True

    def test_larger_shift_stronger_rejection(
        self, detector: StructuralBreakDetector
    ) -> None:
        y_small, x, bp = _mean_shift_data(n=200, shift=1.0, seed=0)
        y_large, _, _ = _mean_shift_data(n=200, shift=10.0, seed=0)
        result_small = detector.chow_test(y_small, x, bp)
        result_large = detector.chow_test(y_large, x, bp)
        assert result_large["f_stat"] > result_small["f_stat"]

    def test_multivariate_regressors(
        self, detector: StructuralBreakDetector
    ) -> None:
        """Chow test works with multiple regressors."""
        rng = np.random.default_rng(42)
        n = 200
        x1 = rng.normal(0, 1, n)
        x2 = rng.normal(0, 1, n)
        x = np.column_stack([x1, x2, np.ones(n)])
        # Shift in intercept at midpoint
        y = np.concatenate([
            1.0 * x1[:100] + 2.0 * x2[:100] + 0.0 + rng.normal(0, 0.5, 100),
            1.0 * x1[100:] + 2.0 * x2[100:] + 5.0 + rng.normal(0, 0.5, 100),
        ])
        result = detector.chow_test(y, x, breakpoint=100)
        assert result["is_break"] is True


# ---------------------------------------------------------------------------
# SADF test
# ---------------------------------------------------------------------------


class TestSadfTest:
    """Test 3-4: SADF detects explosive bubbles."""

    def test_detects_bubble(self, detector: StructuralBreakDetector) -> None:
        """SADF returns explosive for simulated bubble data."""
        prices = _bubble_prices(n=200, seed=0)
        result = detector.sadf_test(prices, min_window=20)

        assert "sadf_stat" in result
        assert "critical_values" in result
        assert "is_explosive" in result
        assert "adf_sequence" in result
        assert "breakpoint_idx" in result
        assert result["is_explosive"] is True

    def test_random_walk_not_explosive(
        self, detector: StructuralBreakDetector
    ) -> None:
        """SADF does not flag a pure random walk as explosive."""
        prices = _random_walk_prices(n=300, seed=0)
        result = detector.sadf_test(prices, min_window=20)
        assert result["is_explosive"] is False

    def test_returns_required_keys(
        self, detector: StructuralBreakDetector
    ) -> None:
        prices = _random_walk_prices(n=100)
        result = detector.sadf_test(prices, min_window=20)
        expected_keys = {
            "sadf_stat", "critical_values", "is_explosive",
            "adf_sequence", "breakpoint_idx",
        }
        assert expected_keys <= result.keys()

    def test_critical_values_keys(
        self, detector: StructuralBreakDetector
    ) -> None:
        prices = _random_walk_prices(n=100)
        result = detector.sadf_test(prices, min_window=20)
        assert {"90%", "95%", "99%"} <= result["critical_values"].keys()

    def test_adf_sequence_length(
        self, detector: StructuralBreakDetector
    ) -> None:
        """ADF sequence should have entries for each expanding window."""
        prices = _random_walk_prices(n=100)
        result = detector.sadf_test(prices, min_window=20)
        # Should have roughly (100 - 20 + 1) = 81 entries (some may fail)
        assert len(result["adf_sequence"]) > 0
        assert len(result["adf_sequence"]) <= 81

    def test_missing_column_raises(
        self, detector: StructuralBreakDetector
    ) -> None:
        prices = pl.DataFrame({"open": [1.0, 2.0, 3.0]})
        with pytest.raises(ValueError, match="close"):
            detector.sadf_test(prices, min_window=20, price_col="close")

    def test_short_series_raises(
        self, detector: StructuralBreakDetector
    ) -> None:
        prices = pl.DataFrame({"close": [100.0] * 10})
        with pytest.raises(ValueError):
            detector.sadf_test(prices, min_window=20)

    def test_bubble_sadf_stat_higher_than_random_walk(
        self, detector: StructuralBreakDetector
    ) -> None:
        """Bubble data should produce a higher SADF stat than random walk."""
        bubble = _bubble_prices(n=200, seed=0)
        rw = _random_walk_prices(n=200, seed=0)
        sadf_bubble = detector.sadf_test(bubble, min_window=20)["sadf_stat"]
        sadf_rw = detector.sadf_test(rw, min_window=20)["sadf_stat"]
        assert sadf_bubble > sadf_rw

    def test_custom_price_col(
        self, detector: StructuralBreakDetector
    ) -> None:
        """Works with a non-default price column name."""
        rng = np.random.default_rng(0)
        prices = pl.DataFrame({
            "adj_close": 100.0 + np.cumsum(rng.normal(0, 1, 100)),
        })
        result = detector.sadf_test(prices, min_window=20, price_col="adj_close")
        assert isinstance(result["sadf_stat"], float)

    def test_max_window_limits_scan(
        self, detector: StructuralBreakDetector
    ) -> None:
        prices = _random_walk_prices(n=200, seed=0)
        result_full = detector.sadf_test(prices, min_window=20)
        result_limited = detector.sadf_test(prices, min_window=20, max_window=100)
        assert len(result_limited["adf_sequence"]) <= len(result_full["adf_sequence"])


# ---------------------------------------------------------------------------
# CUSUM on residuals
# ---------------------------------------------------------------------------


class TestCusumOnResiduals:
    """Test 5-6: CUSUM detects coefficient changes."""

    def test_detects_slope_change(
        self, detector: StructuralBreakDetector
    ) -> None:
        """CUSUM flags break when regression slope changes."""
        y, x = _slope_change_data(n=300, window=60, seed=0)
        result = detector.cusum_on_residuals(y, x, window=60)

        assert "cusum_series" in result
        assert "upper_band" in result
        assert "lower_band" in result
        assert "break_indices" in result
        assert "is_stable" in result
        assert result["is_stable"] is False
        assert len(result["break_indices"]) > 0

    def test_stable_for_stationary_residuals(
        self, detector: StructuralBreakDetector
    ) -> None:
        """CUSUM stays within bands for stable coefficient data."""
        y, x = _stationary_regression_data(n=300, seed=0)
        result = detector.cusum_on_residuals(y, x, window=60)
        assert result["is_stable"] is True
        assert len(result["break_indices"]) == 0

    def test_returns_required_keys(
        self, detector: StructuralBreakDetector
    ) -> None:
        y, x = _stationary_regression_data(n=200)
        result = detector.cusum_on_residuals(y, x, window=60)
        expected_keys = {
            "cusum_series", "upper_band", "lower_band",
            "break_indices", "is_stable",
        }
        assert expected_keys <= result.keys()

    def test_cusum_series_length(
        self, detector: StructuralBreakDetector
    ) -> None:
        """CUSUM series length = n - window."""
        n = 200
        window = 60
        y, x = _stationary_regression_data(n=n)
        result = detector.cusum_on_residuals(y, x, window=window)
        assert len(result["cusum_series"]) == n - window

    def test_bands_symmetric(
        self, detector: StructuralBreakDetector
    ) -> None:
        y, x = _stationary_regression_data(n=200)
        result = detector.cusum_on_residuals(y, x, window=60)
        np.testing.assert_array_almost_equal(
            result["upper_band"], -result["lower_band"]
        )

    def test_shape_mismatch_raises(
        self, detector: StructuralBreakDetector
    ) -> None:
        with pytest.raises(ValueError, match="Shape mismatch"):
            detector.cusum_on_residuals(
                np.ones(100), np.ones((50, 1)), window=20
            )

    def test_window_too_small_raises(
        self, detector: StructuralBreakDetector
    ) -> None:
        y = np.ones(100)
        x = np.column_stack([np.ones(100), np.arange(100, dtype=float)])
        with pytest.raises(ValueError, match="Window"):
            detector.cusum_on_residuals(y, x, window=1)

    def test_series_too_short_raises(
        self, detector: StructuralBreakDetector
    ) -> None:
        y = np.ones(50)
        x = np.ones((50, 1))
        with pytest.raises(ValueError, match="length"):
            detector.cusum_on_residuals(y, x, window=60)

    def test_1d_x_auto_reshape(
        self, detector: StructuralBreakDetector
    ) -> None:
        """1D x array is auto-reshaped to (n, 1)."""
        y, x = _stationary_regression_data(n=200)
        result = detector.cusum_on_residuals(y, x[:, 0], window=60)
        assert "cusum_series" in result


# ---------------------------------------------------------------------------
# detect_regimes
# ---------------------------------------------------------------------------


class TestDetectRegimes:
    """Test 7-8: High-level regime detection."""

    def test_explosive_data_labelled_explosive(
        self, detector: StructuralBreakDetector
    ) -> None:
        """Bubble data should be labelled as explosive."""
        prices = _bubble_prices(n=200, seed=0)
        result = detector.detect_regimes(prices, method="sadf")

        assert isinstance(result, pl.DataFrame)
        assert {"date", "regime", "confidence", "method"} <= set(result.columns)
        assert len(result) == 200
        # At least some rows labelled explosive
        regimes = result["regime"].unique().to_list()
        assert "explosive" in regimes

    def test_random_walk_labelled_normal(
        self, detector: StructuralBreakDetector
    ) -> None:
        """Random walk should be labelled as normal (not explosive, not stationary)."""
        prices = _random_walk_prices(n=300, seed=0)
        result = detector.detect_regimes(prices, method="sadf")

        regimes = result["regime"].unique().to_list()
        assert "explosive" not in regimes

    def test_mean_reverting_detected(
        self, detector: StructuralBreakDetector
    ) -> None:
        """Mean-reverting OU process should be labelled mean_reverting."""
        prices = _mean_reverting_prices(n=500, seed=0)
        result = detector.detect_regimes(prices)
        regimes = result["regime"].unique().to_list()
        assert "mean_reverting" in regimes

    def test_output_columns(
        self, detector: StructuralBreakDetector
    ) -> None:
        prices = _random_walk_prices(n=100)
        result = detector.detect_regimes(prices)
        assert result.columns == ["date", "regime", "confidence", "method"]

    def test_method_column_value(
        self, detector: StructuralBreakDetector
    ) -> None:
        prices = _random_walk_prices(n=100)
        result = detector.detect_regimes(prices, method="sadf")
        assert all(m == "sadf" for m in result["method"].to_list())

    def test_confidence_bounded(
        self, detector: StructuralBreakDetector
    ) -> None:
        prices = _random_walk_prices(n=100)
        result = detector.detect_regimes(prices)
        conf = result["confidence"].to_numpy()
        assert np.all(conf >= 0.0) and np.all(conf <= 1.0)

    def test_missing_price_col_raises(
        self, detector: StructuralBreakDetector
    ) -> None:
        prices = pl.DataFrame({"open": [1.0, 2.0, 3.0]})
        with pytest.raises(ValueError, match="close"):
            detector.detect_regimes(prices, price_col="close")

    def test_too_few_observations_raises(
        self, detector: StructuralBreakDetector
    ) -> None:
        prices = pl.DataFrame({"close": [100.0] * 10})
        with pytest.raises(ValueError, match="20"):
            detector.detect_regimes(prices)

    def test_works_without_date_column(
        self, detector: StructuralBreakDetector
    ) -> None:
        """If no date column, should use integer indices."""
        prices = pl.DataFrame({"close": np.arange(50, dtype=float) + 50.0})
        result = detector.detect_regimes(prices)
        assert len(result) == 50


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test 9: Edge cases — very short series, constant prices."""

    def test_constant_prices_sadf(
        self, detector: StructuralBreakDetector
    ) -> None:
        """Constant prices should not be flagged as explosive."""
        prices = pl.DataFrame({"close": [100.0] * 50})
        # adf_test may fail on constant data; SADF should handle gracefully
        # or raise a clear error
        try:
            result = detector.sadf_test(prices, min_window=20)
            assert result["is_explosive"] is False
        except ValueError:
            pass  # acceptable to raise on degenerate input

    def test_very_short_chow(
        self, detector: StructuralBreakDetector
    ) -> None:
        """Chow test on minimal viable data."""
        rng = np.random.default_rng(0)
        y = rng.normal(0, 1, 10)
        x = np.ones((10, 1))
        result = detector.chow_test(y, x, breakpoint=5)
        assert isinstance(result["f_stat"], float)

    def test_cusum_constant_residuals(
        self, detector: StructuralBreakDetector
    ) -> None:
        """Perfect fit (zero residuals) should report stable."""
        n = 100
        x = np.column_stack([np.arange(n, dtype=float), np.ones(n)])
        y = 2.0 * np.arange(n, dtype=float) + 1.0  # exact linear
        result = detector.cusum_on_residuals(y, x, window=20)
        assert result["is_stable"] is True

    def test_sadf_min_window_equals_series_length(
        self, detector: StructuralBreakDetector
    ) -> None:
        """When min_window == series length, should still work (single ADF)."""
        prices = pl.DataFrame({
            "close": np.arange(25, dtype=float) + 100.0,
        })
        result = detector.sadf_test(prices, min_window=25)
        assert len(result["adf_sequence"]) >= 1
