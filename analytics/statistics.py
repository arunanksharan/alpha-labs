"""Statistical hypothesis testing for financial time series.

Provides stationarity tests, cointegration analysis, normality tests,
and mean-reversion diagnostics. All inputs are polars Series.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy import stats as scipy_stats
from statsmodels.tsa.stattools import adfuller, kpss as kpss_test_
from statsmodels.tsa.vector_ar.vecm import coint_johansen


def _to_numpy(series: pl.Series) -> np.ndarray:
    arr = series.drop_nulls().to_numpy().astype(np.float64)
    if len(arr) == 0:
        raise ValueError("Series is empty after dropping nulls")
    return arr


# ---------------------------------------------------------------------------
# Stationarity
# ---------------------------------------------------------------------------

def adf_test(series: pl.Series, regression: str = "c") -> dict:
    arr = _to_numpy(series)
    if len(arr) < 20:
        raise ValueError("ADF test requires at least 20 observations")

    result = adfuller(arr, regression=regression, autolag="AIC")
    stat, p_value, _, _, critical_values, _ = result
    return {
        "test_stat": float(stat),
        "p_value": float(p_value),
        "critical_values": {k: float(v) for k, v in critical_values.items()},
        "is_stationary": bool(p_value < 0.05),
    }


def kpss_test(series: pl.Series) -> dict:
    arr = _to_numpy(series)
    if len(arr) < 20:
        raise ValueError("KPSS test requires at least 20 observations")

    stat, p_value, _, critical_values = kpss_test_(arr, regression="c", nlags="auto")
    return {
        "test_stat": float(stat),
        "p_value": float(p_value),
        "critical_values": {k: float(v) for k, v in critical_values.items()},
        "is_stationary": bool(p_value > 0.05),
    }


def rolling_adf(series: pl.Series, window: int = 252) -> pl.DataFrame:
    arr = _to_numpy(series)
    if len(arr) < window:
        raise ValueError(f"Series length {len(arr)} < window {window}")

    n = len(arr)
    test_stats = np.full(n, np.nan)
    p_values = np.full(n, np.nan)

    for i in range(window - 1, n):
        segment = arr[i - window + 1 : i + 1]
        if np.std(segment) == 0.0:
            continue
        try:
            result = adfuller(segment, regression="c", autolag="AIC")
            test_stats[i] = result[0]
            p_values[i] = result[1]
        except Exception:
            continue

    return pl.DataFrame({
        "index": list(range(n)),
        "adf_stat": test_stats,
        "adf_pvalue": p_values,
        "is_stationary": [
            p < 0.05 if not np.isnan(p) else None for p in p_values
        ],
    })


# ---------------------------------------------------------------------------
# Hurst exponent (R/S analysis from scratch)
# ---------------------------------------------------------------------------

def hurst_exponent(series: pl.Series, max_lag: int = 100) -> float:
    arr = _to_numpy(series)
    n = len(arr)
    if n < 20:
        raise ValueError("Hurst exponent requires at least 20 observations")

    max_lag = min(max_lag, n // 2)
    lags = []
    rs_values = []

    for lag in range(2, max_lag + 1):
        num_segments = n // lag
        if num_segments == 0:
            continue

        rs_seg = []
        for seg_idx in range(num_segments):
            segment = arr[seg_idx * lag : (seg_idx + 1) * lag]
            mean = np.mean(segment)
            deviations = segment - mean
            cumulative = np.cumsum(deviations)
            r = np.max(cumulative) - np.min(cumulative)
            s = np.std(segment, ddof=1)
            if s > 0:
                rs_seg.append(r / s)

        if rs_seg:
            lags.append(lag)
            rs_values.append(np.mean(rs_seg))

    if len(lags) < 2:
        raise ValueError("Insufficient data to compute Hurst exponent")

    log_lags = np.log(lags)
    log_rs = np.log(rs_values)
    slope, _, _, _, _ = scipy_stats.linregress(log_lags, log_rs)
    return float(slope)


# ---------------------------------------------------------------------------
# Normality and distribution tests
# ---------------------------------------------------------------------------

def jarque_bera_test(series: pl.Series) -> dict:
    arr = _to_numpy(series)
    if len(arr) < 8:
        raise ValueError("Jarque-Bera test requires at least 8 observations")

    stat, p_value = scipy_stats.jarque_bera(arr)
    skew = float(scipy_stats.skew(arr))
    kurt = float(scipy_stats.kurtosis(arr))
    return {
        "stat": float(stat),
        "p_value": float(p_value),
        "skewness": skew,
        "kurtosis": kurt,
        "is_normal": bool(p_value > 0.05),
    }


def ks_test(series1: pl.Series, series2: pl.Series) -> dict:
    arr1 = _to_numpy(series1)
    arr2 = _to_numpy(series2)
    stat, p_value = scipy_stats.ks_2samp(arr1, arr2)
    return {
        "stat": float(stat),
        "p_value": float(p_value),
        "is_same_distribution": bool(p_value > 0.05),
    }


# ---------------------------------------------------------------------------
# Autocorrelation
# ---------------------------------------------------------------------------

def ljung_box_test(series: pl.Series, lags: int = 10) -> dict:
    arr = _to_numpy(series)
    n = len(arr)
    if n < lags + 1:
        raise ValueError(f"Need at least {lags + 1} observations for {lags} lags")

    mean = np.mean(arr)
    c0 = np.sum((arr - mean) ** 2) / n
    if c0 == 0.0:
        return {"stat": 0.0, "p_value": 1.0, "is_autocorrelated": False}

    acf = np.array([
        np.sum((arr[k:] - mean) * (arr[: n - k] - mean)) / (n * c0)
        for k in range(1, lags + 1)
    ])
    q = n * (n + 2) * np.sum(acf**2 / np.arange(n - 1, n - lags - 1, -1))
    p_value = float(1.0 - scipy_stats.chi2.cdf(q, df=lags))
    return {
        "stat": float(q),
        "p_value": p_value,
        "is_autocorrelated": bool(p_value < 0.05),
    }


# ---------------------------------------------------------------------------
# Cointegration
# ---------------------------------------------------------------------------

def engle_granger_cointegration(series1: pl.Series, series2: pl.Series) -> dict:
    y = _to_numpy(series1)
    x = _to_numpy(series2)
    min_len = min(len(y), len(x))
    y, x = y[:min_len], x[:min_len]

    if min_len < 25:
        raise ValueError("Engle-Granger test requires at least 25 observations")

    x_with_const = np.column_stack([x, np.ones(min_len)])
    beta, _, _, _ = np.linalg.lstsq(x_with_const, y, rcond=None)
    hedge_ratio = float(beta[0])
    residuals = y - x_with_const @ beta

    result = adfuller(residuals, regression="c", autolag="AIC")
    stat, p_value = result[0], result[1]

    return {
        "test_stat": float(stat),
        "p_value": float(p_value),
        "is_cointegrated": bool(p_value < 0.05),
        "hedge_ratio": hedge_ratio,
    }


def johansen_cointegration(series: list[pl.Series]) -> dict:
    if len(series) < 2:
        raise ValueError("Johansen test requires at least 2 series")

    arrays = [_to_numpy(s) for s in series]
    min_len = min(len(a) for a in arrays)
    if min_len < 30:
        raise ValueError("Johansen test requires at least 30 observations")

    data = np.column_stack([a[:min_len] for a in arrays])
    result = coint_johansen(data, det_order=0, k_ar_diff=1)

    trace_stats = result.lr1.tolist()
    trace_cv = result.cvt.tolist()
    max_eigen_stats = result.lr2.tolist()
    max_eigen_cv = result.cvm.tolist()

    num_vars = len(series)
    trace_results = []
    for i in range(num_vars):
        trace_results.append({
            "rank": i,
            "trace_stat": float(trace_stats[i]),
            "critical_values": {
                "90%": float(trace_cv[i][0]),
                "95%": float(trace_cv[i][1]),
                "99%": float(trace_cv[i][2]),
            },
            "reject_null": trace_stats[i] > trace_cv[i][1],
        })

    max_eigen_results = []
    for i in range(num_vars):
        max_eigen_results.append({
            "rank": i,
            "max_eigen_stat": float(max_eigen_stats[i]),
            "critical_values": {
                "90%": float(max_eigen_cv[i][0]),
                "95%": float(max_eigen_cv[i][1]),
                "99%": float(max_eigen_cv[i][2]),
            },
            "reject_null": max_eigen_stats[i] > max_eigen_cv[i][1],
        })

    cointegrating_rank = sum(1 for r in trace_results if r["reject_null"])

    return {
        "trace_test": trace_results,
        "max_eigenvalue_test": max_eigen_results,
        "cointegrating_rank": cointegrating_rank,
        "eigenvectors": result.evec.tolist(),
    }


# ---------------------------------------------------------------------------
# Mean reversion
# ---------------------------------------------------------------------------

def half_life_mean_reversion(series: pl.Series) -> float:
    arr = _to_numpy(series)
    if len(arr) < 10:
        raise ValueError("Half-life estimation requires at least 10 observations")

    y = np.diff(arr)
    x = arr[:-1]
    x_with_const = np.column_stack([x, np.ones(len(x))])
    beta, _, _, _ = np.linalg.lstsq(x_with_const, y, rcond=None)
    lam = float(beta[0])

    if lam >= 0:
        return float("inf")

    return float(-np.log(2) / lam)
