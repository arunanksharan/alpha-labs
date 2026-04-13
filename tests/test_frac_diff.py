"""Tests for fractional differentiation (AFML Ch 5).

Covers weight computation, fixed/expanding window FFD, minimum-d search,
and the FracDiffFeature registry integration.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from features.technical.frac_diff import FracDiffFeature, FractionalDifferentiator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df(prices: list[float]) -> pl.DataFrame:
    return pl.DataFrame({"close": prices})


def _random_walk(n: int = 500, seed: int = 42) -> pl.Series:
    """Generate a non-stationary random walk."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, 1, n)
    prices = 100.0 + np.cumsum(steps)
    return pl.Series("close", prices)


def _stationary_series(n: int = 500, seed: int = 42) -> pl.Series:
    """Generate a stationary AR(1) series with strong mean reversion."""
    rng = np.random.default_rng(seed)
    values = np.zeros(n)
    values[0] = 0.0
    for i in range(1, n):
        values[i] = 0.1 * values[i - 1] + rng.normal(0, 1)
    return pl.Series("close", values)


# ---------------------------------------------------------------------------
# Weight computation
# ---------------------------------------------------------------------------

class TestComputeWeights:
    def test_first_weight_is_one(self) -> None:
        weights = FractionalDifferentiator.compute_weights(0.5, 100)
        assert weights[0] == 1.0

    def test_weights_decay_geometrically(self) -> None:
        weights = FractionalDifferentiator.compute_weights(0.5, 100)
        abs_weights = np.abs(weights)
        # Each successive |weight| should be smaller than the previous
        for i in range(1, len(abs_weights)):
            assert abs_weights[i] < abs_weights[i - 1]

    def test_weights_sum_is_finite(self) -> None:
        weights = FractionalDifferentiator.compute_weights(0.5, 10000, threshold=1e-10)
        assert np.isfinite(np.sum(weights))

    def test_weights_above_threshold(self) -> None:
        threshold = 1e-5
        weights = FractionalDifferentiator.compute_weights(0.5, 10000, threshold=threshold)
        # All weights except possibly the first should be above threshold
        # (first is always 1.0, last one added is >= threshold)
        assert all(abs(w) >= threshold for w in weights)

    def test_d_zero_single_weight(self) -> None:
        """d=0 means w_0=1, w_1 = -1*(0-1+1)/1 = 0 => stops."""
        weights = FractionalDifferentiator.compute_weights(0.0, 100)
        assert len(weights) == 1
        assert weights[0] == 1.0

    def test_d_one_weights(self) -> None:
        """d=1 gives w_0=1, w_1=-1, w_2=0 => stops at w_2."""
        weights = FractionalDifferentiator.compute_weights(1.0, 100)
        assert len(weights) == 2
        np.testing.assert_allclose(weights, [1.0, -1.0])

    def test_threshold_controls_length(self) -> None:
        w_tight = FractionalDifferentiator.compute_weights(0.5, 10000, threshold=1e-3)
        w_loose = FractionalDifferentiator.compute_weights(0.5, 10000, threshold=1e-8)
        assert len(w_tight) < len(w_loose)

    def test_size_caps_length(self) -> None:
        weights = FractionalDifferentiator.compute_weights(0.5, 5, threshold=1e-20)
        assert len(weights) <= 5


# ---------------------------------------------------------------------------
# Fixed-window FFD
# ---------------------------------------------------------------------------

class TestFracDiffFixedWindow:
    def test_d_one_equals_first_difference(self) -> None:
        """d=1.0 should produce the same result as standard first-differencing."""
        prices = [100.0, 102.0, 101.0, 105.0, 103.0, 107.0, 110.0, 108.0]
        series = pl.Series("close", prices)
        result = FractionalDifferentiator.frac_diff_fixed_window(series, d=1.0, window=2)

        expected_diff = np.diff(prices)
        result_arr = result.to_numpy()

        # First value is null (warmup)
        assert np.isnan(result_arr[0])
        # Remaining values match first difference
        np.testing.assert_allclose(result_arr[1:], expected_diff, atol=1e-10)

    def test_d_zero_returns_original(self) -> None:
        """d=0.0 should return the original series (identity transform).

        With d=0, weights are [1, 0, 0, ...] so the dot product equals x_t.
        Use a small window to minimize warmup nulls.
        """
        prices = [100.0, 102.0, 101.0, 105.0, 103.0, 107.0, 110.0]
        series = pl.Series("close", prices)
        # Use window=1 so only w_0=1 is applied, no warmup needed.
        # But fixed window always generates `window` weights, so window=1
        # means weights = [1.0] (single element), and all values are valid.
        result = FractionalDifferentiator.frac_diff_fixed_window(series, d=0.0, window=1)

        result_arr = result.to_numpy()
        # d=0 weights: w_0=1, then w_1 = -1*(0-1+1)/1 = 0 => loop body
        # generates [1.0] only (since k goes from 1 to window=1, which is empty range).
        # So weight vector length = 1, no warmup.
        np.testing.assert_allclose(result_arr, np.array(prices), atol=1e-10)

    def test_output_length_matches_input(self) -> None:
        series = pl.Series("close", list(range(50)))
        result = FractionalDifferentiator.frac_diff_fixed_window(series, d=0.5, window=10)
        assert len(result) == len(series)

    def test_warmup_nulls(self) -> None:
        """First (window-1) values should be null."""
        series = pl.Series("close", [float(x) for x in range(20)])
        window = 5
        result = FractionalDifferentiator.frac_diff_fixed_window(series, d=0.5, window=window)
        result_arr = result.to_numpy()
        assert all(np.isnan(result_arr[i]) for i in range(window - 1))
        assert not np.isnan(result_arr[window - 1])

    def test_preserves_series_name(self) -> None:
        series = pl.Series("my_prices", [1.0, 2.0, 3.0, 4.0, 5.0])
        result = FractionalDifferentiator.frac_diff_fixed_window(series, d=0.3, window=3)
        assert result.name == "my_prices"

    def test_monotonic_prices_positive_with_positive_d(self) -> None:
        """Differencing a strictly increasing series should give positive values
        after warmup period."""
        prices = [float(x) for x in range(1, 21)]
        series = pl.Series("close", prices)
        result = FractionalDifferentiator.frac_diff_fixed_window(series, d=0.5, window=5)
        # Filter out NaN warmup values
        valid = result.drop_nans()
        assert all(v > 0 for v in valid.to_list())


# ---------------------------------------------------------------------------
# Expanding-window FFD
# ---------------------------------------------------------------------------

class TestFracDiffExpanding:
    def test_output_length_matches_input(self) -> None:
        series = pl.Series("close", [float(x) for x in range(50)])
        result = FractionalDifferentiator.frac_diff_expanding(series, d=0.5)
        assert len(result) == len(series)

    def test_d_one_equals_first_difference(self) -> None:
        """d=1.0 expanding should also match first-difference."""
        prices = [100.0, 102.0, 101.0, 105.0, 103.0]
        series = pl.Series("close", prices)
        result = FractionalDifferentiator.frac_diff_expanding(series, d=1.0)

        expected_diff = np.diff(prices)
        result_arr = result.to_numpy()
        # First value is null
        assert np.isnan(result_arr[0])
        np.testing.assert_allclose(result_arr[1:], expected_diff, atol=1e-10)

    def test_expanding_has_more_non_null_than_large_fixed(self) -> None:
        """Expanding window should start producing values earlier than a
        large fixed window when threshold is generous."""
        series = pl.Series("close", [float(x) for x in range(100)])
        expanding = FractionalDifferentiator.frac_diff_expanding(series, d=0.5, threshold=1e-2)
        fixed = FractionalDifferentiator.frac_diff_fixed_window(series, d=0.5, window=50)
        # Expanding with generous threshold has shorter effective window
        assert expanding.drop_nulls().len() >= fixed.drop_nulls().len()


# ---------------------------------------------------------------------------
# find_min_d
# ---------------------------------------------------------------------------

class TestFindMinD:
    def test_random_walk_needs_nonzero_d(self) -> None:
        """A random walk should need d > 0 for stationarity.

        Note: with fixed-window FFD (window=100), d can be lower than 1.0
        because the window truncation limits effective memory. The key
        property is that d > 0 (non-trivial differencing is required).
        """
        series = _random_walk(1000)
        d = FractionalDifferentiator.find_min_d(series, step=0.1)
        assert d > 0.0, f"Random walk should need d > 0, got {d}"

    def test_stationary_series_needs_low_d(self) -> None:
        """An already stationary series should need d close to 0.0."""
        series = _stationary_series(500)
        d = FractionalDifferentiator.find_min_d(series, step=0.05)
        assert d <= 0.15, f"Stationary series should need d <= 0.15, got {d}"

    def test_returns_max_d_when_nothing_works(self) -> None:
        """If no d achieves stationarity, return max_d."""
        # Very short series — ADF will struggle
        series = pl.Series("close", [1.0, 2.0, 3.0, 4.0, 5.0])
        d = FractionalDifferentiator.find_min_d(series, max_d=1.0, step=0.5)
        assert d == 1.0

    def test_custom_significance(self) -> None:
        """Stricter significance should require equal or higher d."""
        series = _random_walk(1000, seed=99)
        d_loose = FractionalDifferentiator.find_min_d(series, step=0.1, significance=0.10)
        d_strict = FractionalDifferentiator.find_min_d(series, step=0.1, significance=0.01)
        assert d_strict >= d_loose


# ---------------------------------------------------------------------------
# FracDiffFeature (registry integration)
# ---------------------------------------------------------------------------

class TestFracDiffFeature:
    def test_properties(self) -> None:
        feat = FracDiffFeature(d=0.5, window=50)
        assert feat.name == "frac_diff_0.5"
        assert feat.lookback_days == 50
        assert feat.category == "technical"

    def test_auto_name(self) -> None:
        feat = FracDiffFeature(d=None)
        assert feat.name == "frac_diff_auto"

    def test_compute_adds_column(self) -> None:
        feat = FracDiffFeature(d=0.5, window=10)
        df = _make_df([float(x) for x in range(50)])
        result = feat.compute(df)
        assert "frac_diff" in result.columns
        assert "close" in result.columns
        assert len(result) == 50

    def test_compute_preserves_other_columns(self) -> None:
        feat = FracDiffFeature(d=0.5, window=5)
        df = pl.DataFrame({
            "date": list(range(20)),
            "close": [float(x) for x in range(20)],
            "volume": [1000.0] * 20,
        })
        result = feat.compute(df)
        assert "date" in result.columns
        assert "volume" in result.columns
        assert "frac_diff" in result.columns

    def test_compute_auto_d(self) -> None:
        """Auto-d mode should still produce a valid result."""
        rng = np.random.default_rng(42)
        prices = 100.0 + np.cumsum(rng.normal(0, 1, 500))
        feat = FracDiffFeature(d=None, window=50)
        result = feat.compute(_make_df(prices.tolist()))
        assert "frac_diff" in result.columns
        # Should have some non-null values
        assert result["frac_diff"].drop_nulls().len() > 0

    def test_validate_insufficient_data(self) -> None:
        feat = FracDiffFeature(d=0.5, window=100)
        df = _make_df([100.0] * 99)
        assert feat.validate(df) is False

    def test_validate_sufficient_data(self) -> None:
        feat = FracDiffFeature(d=0.5, window=100)
        df = _make_df([100.0] * 100)
        assert feat.validate(df) is True

    def test_registry_integration(self) -> None:
        """FracDiffFeature should be registered in FeatureRegistry."""
        from core.features import FeatureRegistry

        features = FeatureRegistry.list_features(category="technical")
        # The default instance (d=None) registers as "frac_diff_auto"
        assert "frac_diff_auto" in features

    def test_registry_get(self) -> None:
        from core.features import FeatureRegistry

        feat = FeatureRegistry.get("frac_diff_auto", d=0.3, window=20)
        assert isinstance(feat, FracDiffFeature)
        assert feat.name == "frac_diff_0.3"

    def test_custom_price_col(self) -> None:
        feat = FracDiffFeature(d=0.5, window=5, price_col="adj_close")
        df = pl.DataFrame({"adj_close": [float(x) for x in range(20)]})
        result = feat.compute(df)
        assert "frac_diff" in result.columns
