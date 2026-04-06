"""Tests for analytics/statistics.py.

Synthetic series with KNOWN statistical properties are used so assertions
are grounded in the data-generating process rather than arbitrary thresholds.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from analytics.statistics import (
    adf_test,
    engle_granger_cointegration,
    half_life_mean_reversion,
    hurst_exponent,
    jarque_bera_test,
    ks_test,
    kpss_test,
    ljung_box_test,
)


# ---------------------------------------------------------------------------
# Synthetic data factories
# ---------------------------------------------------------------------------

def _white_noise(n: int = 500, seed: int = 0) -> pl.Series:
    rng = np.random.default_rng(seed)
    return pl.Series("wn", rng.normal(0.0, 1.0, n))


def _random_walk(n: int = 500, seed: int = 0) -> pl.Series:
    rng = np.random.default_rng(seed)
    return pl.Series("rw", np.cumsum(rng.normal(0.0, 1.0, n)))


def _ar1_stationary(n: int = 500, phi: float = 0.5, seed: int = 0) -> pl.Series:
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    eps = rng.normal(0.0, 1.0, n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t]
    return pl.Series("ar1", x)


def _trending_series(n: int = 500, seed: int = 0) -> pl.Series:
    rng = np.random.default_rng(seed)
    trend = np.linspace(0, 20, n)
    noise = rng.normal(0.0, 0.5, n)
    return pl.Series("trend", trend + noise)


def _mean_reverting_ou(n: int = 1000, theta: float = 0.3, mu: float = 0.0, seed: int = 0) -> pl.Series:
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    eps = rng.normal(0.0, 1.0, n)
    for t in range(1, n):
        x[t] = x[t - 1] + theta * (mu - x[t - 1]) + eps[t]
    return pl.Series("ou", x)


def _cointegrated_pair(n: int = 500, seed: int = 0) -> tuple[pl.Series, pl.Series]:
    rng = np.random.default_rng(seed)
    common = np.cumsum(rng.normal(0.0, 1.0, n))
    s1 = common + rng.normal(0.0, 0.5, n)
    s2 = 2.0 * common + rng.normal(0.0, 0.5, n)
    return pl.Series("s1", s1), pl.Series("s2", s2)


# ---------------------------------------------------------------------------
# adf_test
# ---------------------------------------------------------------------------

class TestAdfTest:
    def test_returns_required_keys(self) -> None:
        result = adf_test(_white_noise())
        assert {"test_stat", "p_value", "critical_values", "is_stationary"} <= result.keys()

    def test_stationary_series_is_stationary(self) -> None:
        result = adf_test(_white_noise(500, seed=0))
        assert result["is_stationary"] is True

    def test_random_walk_not_stationary(self) -> None:
        rng = np.random.default_rng(42)
        result = adf_test(pl.Series("rw", np.cumsum(rng.normal(0, 1, 500))))
        assert result["is_stationary"] is False

    def test_stationary_ar1_is_stationary(self) -> None:
        result = adf_test(_ar1_stationary(n=500, phi=0.3, seed=1))
        assert result["is_stationary"] is True

    def test_p_value_in_unit_interval(self) -> None:
        result = adf_test(_white_noise())
        assert 0.0 <= result["p_value"] <= 1.0

    def test_critical_values_keys_present(self) -> None:
        result = adf_test(_white_noise())
        assert "1%" in result["critical_values"]
        assert "5%" in result["critical_values"]
        assert "10%" in result["critical_values"]

    def test_fewer_than_20_obs_raises(self) -> None:
        with pytest.raises(ValueError, match="20"):
            adf_test(pl.Series("s", [1.0] * 15))

    def test_empty_series_raises(self) -> None:
        with pytest.raises(ValueError):
            adf_test(pl.Series("s", [], dtype=pl.Float64))

    @pytest.mark.parametrize("regression", ["c", "ct", "ctt", "n"])
    def test_regression_variants_return_float_stat(self, regression: str) -> None:
        result = adf_test(_white_noise(200), regression=regression)
        assert isinstance(result["test_stat"], float)

    def test_adf_stat_is_negative_for_stationary(self) -> None:
        result = adf_test(_white_noise(500))
        assert result["test_stat"] < 0


# ---------------------------------------------------------------------------
# kpss_test
# ---------------------------------------------------------------------------

class TestKpssTest:
    def test_returns_required_keys(self) -> None:
        result = kpss_test(_white_noise())
        assert {"test_stat", "p_value", "critical_values", "is_stationary"} <= result.keys()

    def test_stationary_series_passes_kpss(self) -> None:
        result = kpss_test(_white_noise(500, seed=0))
        assert result["is_stationary"] is True

    def test_random_walk_fails_kpss(self) -> None:
        result = kpss_test(_random_walk(500, seed=0))
        assert result["is_stationary"] is False

    def test_p_value_bounded(self) -> None:
        result = kpss_test(_white_noise())
        assert 0.0 <= result["p_value"] <= 1.0

    def test_fewer_than_20_obs_raises(self) -> None:
        with pytest.raises(ValueError, match="20"):
            kpss_test(pl.Series("s", [1.0] * 10))

    def test_adf_and_kpss_agree_on_random_walk(self) -> None:
        rw = _random_walk(500)
        adf_result = adf_test(rw)
        kpss_result = kpss_test(rw)
        assert adf_result["is_stationary"] is False
        assert kpss_result["is_stationary"] is False


# ---------------------------------------------------------------------------
# hurst_exponent
# ---------------------------------------------------------------------------

class TestHurstExponent:
    def test_white_noise_near_half(self) -> None:
        # R/S Hurst on iid returns should be ~0.5
        h = hurst_exponent(_white_noise(n=2000, seed=0))
        assert 0.35 <= h <= 0.65

    def test_random_walk_persistent(self) -> None:
        # R/S Hurst on cumulative sum (random walk) gives H close to 1.0
        h = hurst_exponent(_random_walk(n=2000, seed=0))
        assert h > 0.7

    def test_trending_series_above_half(self) -> None:
        h = hurst_exponent(_trending_series(n=2000, seed=0))
        assert h > 0.55

    def test_mean_reverting_below_trending(self) -> None:
        h_mr = hurst_exponent(_mean_reverting_ou(n=2000, theta=0.5, seed=0))
        h_trend = hurst_exponent(_trending_series(n=2000, seed=0))
        assert h_mr < h_trend

    def test_returns_float(self) -> None:
        assert isinstance(hurst_exponent(_white_noise(200)), float)

    def test_fewer_than_20_obs_raises(self) -> None:
        with pytest.raises(ValueError):
            hurst_exponent(pl.Series("s", [1.0] * 10))

    @pytest.mark.parametrize("seed", [0, 1, 2])
    def test_white_noise_seeds_near_half(self, seed: int) -> None:
        h = hurst_exponent(_white_noise(n=2000, seed=seed))
        assert 0.3 <= h <= 0.75


# ---------------------------------------------------------------------------
# jarque_bera_test
# ---------------------------------------------------------------------------

class TestJarqueBeraTest:
    def test_required_keys(self) -> None:
        result = jarque_bera_test(_white_noise())
        assert {"stat", "p_value", "skewness", "kurtosis", "is_normal"} <= result.keys()

    def test_normal_data_not_rejected(self) -> None:
        rng = np.random.default_rng(0)
        result = jarque_bera_test(pl.Series("n", rng.normal(0, 1, 2000)))
        assert result["is_normal"] is True

    def test_heavy_tailed_data_rejected(self) -> None:
        rng = np.random.default_rng(0)
        result = jarque_bera_test(pl.Series("t", rng.standard_t(df=3, size=2000)))
        assert result["is_normal"] is False

    def test_skewed_data_rejected(self) -> None:
        rng = np.random.default_rng(0)
        result = jarque_bera_test(pl.Series("sk", rng.exponential(scale=1.0, size=1000)))
        assert result["is_normal"] is False

    def test_skewness_positive_for_right_skewed(self) -> None:
        rng = np.random.default_rng(0)
        result = jarque_bera_test(pl.Series("rs", rng.exponential(scale=1.0, size=500)))
        assert result["skewness"] > 0

    def test_normal_excess_kurtosis_near_zero(self) -> None:
        rng = np.random.default_rng(0)
        result = jarque_bera_test(pl.Series("n", rng.normal(0, 1, 3000)))
        assert abs(result["kurtosis"]) < 1.0

    def test_fewer_than_8_obs_raises(self) -> None:
        with pytest.raises(ValueError, match="8"):
            jarque_bera_test(pl.Series("s", [1.0, 2.0, 3.0]))

    def test_p_value_bounded(self) -> None:
        result = jarque_bera_test(_white_noise(200))
        assert 0.0 <= result["p_value"] <= 1.0


# ---------------------------------------------------------------------------
# ks_test
# ---------------------------------------------------------------------------

class TestKsTest:
    def test_required_keys(self) -> None:
        rng = np.random.default_rng(0)
        s1 = pl.Series("a", rng.normal(0, 1, 200))
        s2 = pl.Series("b", rng.normal(0, 1, 200))
        result = ks_test(s1, s2)
        assert {"stat", "p_value", "is_same_distribution"} <= result.keys()

    def test_same_distribution_not_rejected(self) -> None:
        rng = np.random.default_rng(0)
        s1 = pl.Series("a", rng.normal(0, 1, 500))
        s2 = pl.Series("b", rng.normal(0, 1, 500))
        assert ks_test(s1, s2)["is_same_distribution"] is True

    def test_different_means_rejected(self) -> None:
        rng = np.random.default_rng(0)
        s1 = pl.Series("a", rng.normal(0.0, 1.0, 1000))
        s2 = pl.Series("b", rng.normal(5.0, 1.0, 1000))
        assert ks_test(s1, s2)["is_same_distribution"] is False

    def test_normal_vs_uniform_rejected(self) -> None:
        rng = np.random.default_rng(0)
        normal = pl.Series("n", rng.normal(0, 1, 500))
        uniform = pl.Series("u", rng.uniform(-3, 3, 500))
        assert ks_test(normal, uniform)["is_same_distribution"] is False

    def test_stat_in_unit_interval(self) -> None:
        rng = np.random.default_rng(0)
        s1 = pl.Series("a", rng.normal(0, 1, 200))
        s2 = pl.Series("b", rng.normal(0, 1, 200))
        result = ks_test(s1, s2)
        assert 0.0 <= result["stat"] <= 1.0

    def test_empty_series_raises(self) -> None:
        empty = pl.Series("e", [], dtype=pl.Float64)
        with pytest.raises(ValueError):
            ks_test(empty, empty)


# ---------------------------------------------------------------------------
# ljung_box_test
# ---------------------------------------------------------------------------

class TestLjungBoxTest:
    def test_required_keys(self) -> None:
        result = ljung_box_test(_white_noise())
        assert {"stat", "p_value", "is_autocorrelated"} <= result.keys()

    def test_white_noise_no_autocorrelation(self) -> None:
        rng = np.random.default_rng(0)
        result = ljung_box_test(pl.Series("wn", rng.normal(0, 1, 500)), lags=10)
        assert result["is_autocorrelated"] is False

    def test_ar1_highly_autocorrelated(self) -> None:
        result = ljung_box_test(_ar1_stationary(n=500, phi=0.8, seed=0), lags=10)
        assert result["is_autocorrelated"] is True

    def test_constant_series_not_autocorrelated(self) -> None:
        result = ljung_box_test(pl.Series("c", [1.0] * 100), lags=5)
        assert result["is_autocorrelated"] is False

    def test_insufficient_obs_raises(self) -> None:
        with pytest.raises(ValueError):
            ljung_box_test(pl.Series("s", [1.0, 2.0, 3.0]), lags=10)

    def test_p_value_bounded(self) -> None:
        result = ljung_box_test(_white_noise(300))
        assert 0.0 <= result["p_value"] <= 1.0

    @pytest.mark.parametrize("lags", [5, 10, 20])
    def test_various_lag_counts(self, lags: int) -> None:
        result = ljung_box_test(_white_noise(300), lags=lags)
        assert isinstance(result["stat"], float)

    def test_higher_phi_lower_p_value(self) -> None:
        low_phi = ljung_box_test(_ar1_stationary(500, phi=0.2, seed=0), lags=10)
        high_phi = ljung_box_test(_ar1_stationary(500, phi=0.9, seed=0), lags=10)
        assert high_phi["p_value"] < low_phi["p_value"]


# ---------------------------------------------------------------------------
# engle_granger_cointegration
# ---------------------------------------------------------------------------

class TestEngleGrangerCointegration:
    def test_required_keys(self) -> None:
        s1, s2 = _cointegrated_pair(500)
        result = engle_granger_cointegration(s1, s2)
        assert {"test_stat", "p_value", "is_cointegrated", "hedge_ratio"} <= result.keys()

    def test_cointegrated_pair_detected(self) -> None:
        s1, s2 = _cointegrated_pair(n=500, seed=0)
        assert engle_granger_cointegration(s1, s2)["is_cointegrated"] is True

    def test_independent_walks_high_p_value_on_average(self) -> None:
        p_values = []
        for seed in range(20):
            rng = np.random.default_rng(seed + 100)
            s1 = pl.Series("s1", np.cumsum(rng.normal(0, 1, 1000)))
            s2 = pl.Series("s2", np.cumsum(rng.normal(0, 1, 1000)))
            result = engle_granger_cointegration(s1, s2)
            p_values.append(result["p_value"])
        rejection_rate = sum(1 for p in p_values if p < 0.05) / len(p_values)
        assert rejection_rate <= 0.20

    def test_hedge_ratio_is_float(self) -> None:
        s1, s2 = _cointegrated_pair(200)
        result = engle_granger_cointegration(s1, s2)
        assert isinstance(result["hedge_ratio"], float)

    def test_hedge_ratio_near_known_value(self) -> None:
        rng = np.random.default_rng(0)
        common = np.cumsum(rng.normal(0.0, 1.0, 1000))
        s1 = pl.Series("s1", common + rng.normal(0.0, 0.1, 1000))
        s2 = pl.Series("s2", 3.0 * common + rng.normal(0.0, 0.1, 1000))
        result = engle_granger_cointegration(s1, s2)
        assert result["is_cointegrated"] is True
        assert abs(result["hedge_ratio"] - (1.0 / 3.0)) < 0.1

    def test_fewer_than_25_obs_raises(self) -> None:
        s = pl.Series("s", [float(i) for i in range(20)])
        with pytest.raises(ValueError, match="25"):
            engle_granger_cointegration(s, s)

    def test_p_value_bounded(self) -> None:
        s1, s2 = _cointegrated_pair(200)
        result = engle_granger_cointegration(s1, s2)
        assert 0.0 <= result["p_value"] <= 1.0


# ---------------------------------------------------------------------------
# half_life_mean_reversion
# ---------------------------------------------------------------------------

class TestHalfLifeMeanReversion:
    def test_returns_float(self) -> None:
        assert isinstance(half_life_mean_reversion(_mean_reverting_ou(500, theta=0.1)), float)

    def test_faster_reversion_shorter_half_life(self) -> None:
        hl_slow = half_life_mean_reversion(_mean_reverting_ou(n=1000, theta=0.05, seed=0))
        hl_fast = half_life_mean_reversion(_mean_reverting_ou(n=1000, theta=0.5, seed=0))
        assert hl_fast < hl_slow

    def test_positive_half_life_for_mean_reverting(self) -> None:
        series = _mean_reverting_ou(n=500, theta=0.2, seed=0)
        assert half_life_mean_reversion(series) > 0

    def test_random_walk_returns_large_or_inf(self) -> None:
        hl = half_life_mean_reversion(_random_walk(n=500, seed=0))
        assert hl == float("inf") or hl > 100

    def test_fewer_than_10_obs_raises(self) -> None:
        with pytest.raises(ValueError, match="10"):
            half_life_mean_reversion(pl.Series("s", [1.0] * 5))

    def test_empty_series_raises(self) -> None:
        with pytest.raises(ValueError):
            half_life_mean_reversion(pl.Series("s", [], dtype=pl.Float64))

    def test_known_theta_produces_expected_half_life(self) -> None:
        rng = np.random.default_rng(0)
        n = 3000
        theta = 0.05
        x = np.zeros(n)
        eps = rng.normal(0.0, 1.0, n)
        for t in range(1, n):
            x[t] = x[t - 1] + theta * (0.0 - x[t - 1]) + eps[t]
        series = pl.Series("ou", x)
        hl = half_life_mean_reversion(series)
        expected = float(np.log(2) / theta)
        assert abs(hl - expected) < 15.0

    @pytest.mark.parametrize("theta,lo,hi", [
        (0.1, 3.0, 30.0),
        (0.3, 1.0, 15.0),
    ])
    def test_half_life_plausible_range(self, theta: float, lo: float, hi: float) -> None:
        series = _mean_reverting_ou(n=3000, theta=theta, seed=0)
        hl = half_life_mean_reversion(series)
        assert lo <= hl <= hi
