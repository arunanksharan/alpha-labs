"""Structural break detection for financial time series.

Implements AFML Chapter 17 methods: Chow test, Supremum ADF (SADF),
and CUSUM on recursive residuals. Used to detect regime changes,
bubbles, and model instability.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy import stats as scipy_stats

from analytics.statistics import adf_test


def _ols_rss(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, float]:
    """Fit OLS via least squares, return (coefficients, RSS)."""
    beta, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ beta
    rss = float(np.sum(residuals**2))
    return beta, rss


class StructuralBreakDetector:
    """Detect regime changes and bubbles in financial time series.

    Reference: AFML Ch 17

    Three methods:
    1. Chow test -- known breakpoint, tests coefficient stability
    2. SADF (Supremum ADF) -- scans for explosive behavior (bubbles)
    3. CUSUM on residuals -- detects when a model breaks down
    """

    # ------------------------------------------------------------------
    # Chow test
    # ------------------------------------------------------------------

    def chow_test(
        self, y: np.ndarray, x: np.ndarray, breakpoint: int
    ) -> dict:
        """Chow test for structural break at a known point.

        Splits sample at breakpoint, fits OLS on each sub-sample,
        tests whether coefficients are significantly different.

        The test statistic:
            F = ((RSS_pooled - RSS_1 - RSS_2) / k) / ((RSS_1 + RSS_2) / (n - 2k))
        where k = number of parameters, n = total observations.

        Args:
            y: Dependent variable array of shape (n,).
            x: Regressor matrix of shape (n, k). Must include intercept
               column if desired.
            breakpoint: Index at which to split the sample. Must satisfy
                        k < breakpoint < n - k.

        Returns:
            {"f_stat": float, "p_value": float, "is_break": bool}
        """
        y = np.asarray(y, dtype=np.float64)
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(-1, 1)

        n, k = x.shape

        if breakpoint <= k or breakpoint >= n - k:
            raise ValueError(
                f"Breakpoint {breakpoint} invalid for n={n}, k={k}. "
                f"Need k < breakpoint < n - k."
            )

        # Pooled regression
        _, rss_pooled = _ols_rss(y, x)

        # Sub-sample regressions
        _, rss_1 = _ols_rss(y[:breakpoint], x[:breakpoint])
        _, rss_2 = _ols_rss(y[breakpoint:], x[breakpoint:])

        denominator_dof = n - 2 * k
        if denominator_dof <= 0:
            raise ValueError(
                f"Insufficient observations: n={n}, k={k}. "
                f"Need n > 2k for Chow test."
            )

        f_stat = (
            ((rss_pooled - rss_1 - rss_2) / k)
            / ((rss_1 + rss_2) / denominator_dof)
        )
        p_value = float(1.0 - scipy_stats.f.cdf(f_stat, k, denominator_dof))

        return {
            "f_stat": float(f_stat),
            "p_value": p_value,
            "is_break": bool(p_value < 0.05),
        }

    # ------------------------------------------------------------------
    # SADF test
    # ------------------------------------------------------------------

    def sadf_test(
        self,
        prices: pl.DataFrame,
        min_window: int = 20,
        max_window: int | None = None,
        lag: int = 1,
        price_col: str = "close",
        significance: float = 0.05,
    ) -> dict:
        """Supremum ADF test for explosive behavior (bubble detection).

        AFML Section 17.4.2:
        1. Start with min_window observations.
        2. Expand window by 1 observation at a time.
        3. Run ADF test at each window size.
        4. Take the supremum (maximum) of all ADF statistics.
        5. Compare to critical values from Phillips, Shi, Yu (2015).

        A large positive SADF statistic indicates explosive behavior
        (unit root rejection in the explosive direction).

        Args:
            prices: DataFrame containing a price column.
            min_window: Minimum number of observations for the first ADF.
            max_window: Maximum window size. Defaults to full series length.
            lag: Number of lags for the ADF regression.
            price_col: Name of the price column.
            significance: Significance level for is_explosive flag.

        Returns:
            {
                "sadf_stat": float,
                "critical_values": {"90%": float, "95%": float, "99%": float},
                "is_explosive": bool,
                "adf_sequence": list[float],
                "breakpoint_idx": int,
            }
        """
        if price_col not in prices.columns:
            raise ValueError(f"Column '{price_col}' not found in DataFrame")

        raw = prices[price_col].drop_nulls().to_numpy().astype(np.float64)

        if len(raw) < min_window:
            raise ValueError(
                f"Series length {len(raw)} < min_window {min_window}"
            )

        # Use log prices for ADF regression (standard in bubble literature)
        log_prices = np.log(np.maximum(raw, 1e-12))

        if max_window is None:
            max_window = len(log_prices)
        max_window = min(max_window, len(log_prices))

        # Phillips, Shi, Yu (2015) approximate critical values for SADF
        critical_values = {"90%": 0.4, "95%": 1.0, "99%": 1.9}

        adf_sequence: list[float] = []

        for end in range(min_window, max_window + 1):
            segment = log_prices[:end]
            series = pl.Series("seg", segment)
            try:
                result = adf_test(series, regression="c")
                adf_sequence.append(result["test_stat"])
            except (ValueError, Exception):
                # Skip windows that fail (e.g., constant segments)
                continue

        if not adf_sequence:
            raise ValueError("No valid ADF statistics computed. Check input data.")

        sadf_stat = float(max(adf_sequence))
        breakpoint_idx = int(np.argmax(adf_sequence)) + min_window

        # Map significance to critical value key
        sig_map = {0.10: "90%", 0.05: "95%", 0.01: "99%"}
        cv_key = sig_map.get(significance, "95%")
        is_explosive = bool(sadf_stat > critical_values[cv_key])

        return {
            "sadf_stat": sadf_stat,
            "critical_values": critical_values,
            "is_explosive": is_explosive,
            "adf_sequence": adf_sequence,
            "breakpoint_idx": breakpoint_idx,
        }

    # ------------------------------------------------------------------
    # CUSUM on recursive residuals
    # ------------------------------------------------------------------

    def cusum_on_residuals(
        self, y: np.ndarray, x: np.ndarray, window: int = 60
    ) -> dict:
        """CUSUM test on recursive OLS residuals.

        Fits OLS on an expanding window starting from `window` observations.
        At each step, predicts the next observation using coefficients
        estimated on the preceding data. The prediction error is the
        recursive residual. The cumulative sum of standardised recursive
        residuals is compared against significance bands.

        Args:
            y: Dependent variable array of shape (n,).
            x: Regressor matrix of shape (n, k). Must include intercept
               column if desired.
            window: Minimum initial training window.

        Returns:
            {
                "cusum_series": np.ndarray,
                "upper_band": np.ndarray,
                "lower_band": np.ndarray,
                "break_indices": list[int],
                "is_stable": bool,
            }
        """
        y = np.asarray(y, dtype=np.float64)
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(-1, 1)

        n, k = x.shape
        if n != len(y):
            raise ValueError(
                f"Shape mismatch: y has {len(y)} obs, x has {n} rows"
            )
        if window <= k:
            raise ValueError(
                f"Window {window} must be > number of parameters {k}"
            )
        if n <= window:
            raise ValueError(
                f"Series length {n} must be > window {window}"
            )

        # Compute recursive residuals
        recursive_residuals: list[float] = []
        for t in range(window, n):
            x_train = x[:t]
            y_train = y[:t]
            beta, _, _, _ = np.linalg.lstsq(x_train, y_train, rcond=None)
            y_pred = float(x[t] @ beta)
            recursive_residuals.append(y[t] - y_pred)

        rr = np.array(recursive_residuals, dtype=np.float64)
        m = len(rr)

        if m < 2:
            raise ValueError("Not enough recursive residuals to compute CUSUM")

        # Standardise by estimated standard deviation
        sigma = np.std(rr, ddof=1)
        if sigma < 1e-15:
            # Perfectly fitted model => no breaks detectable
            return {
                "cusum_series": np.zeros(m),
                "upper_band": np.ones(m),
                "lower_band": -np.ones(m),
                "break_indices": [],
                "is_stable": True,
            }

        standardised = rr / sigma
        cusum = np.cumsum(standardised)

        # Significance bands: +/- a * sqrt(m) where a ~ 0.948 for 5% level
        # (Brown, Durbin, Evans 1975 critical value table)
        a = 0.948
        band_value = a * np.sqrt(m)
        # Linear bands that widen over time (standard CUSUM presentation)
        t_frac = np.arange(1, m + 1) / m
        upper_band = band_value * (1.0 + 2.0 * t_frac)
        lower_band = -band_value * (1.0 + 2.0 * t_frac)

        # Detect crossings
        break_indices = [
            int(i)
            for i in range(m)
            if cusum[i] > upper_band[i] or cusum[i] < lower_band[i]
        ]

        return {
            "cusum_series": cusum,
            "upper_band": upper_band,
            "lower_band": lower_band,
            "break_indices": break_indices,
            "is_stable": bool(len(break_indices) == 0),
        }

    # ------------------------------------------------------------------
    # High-level regime detector
    # ------------------------------------------------------------------

    def detect_regimes(
        self,
        prices: pl.DataFrame,
        method: str = "sadf",
        price_col: str = "close",
    ) -> pl.DataFrame:
        """High-level regime detector.

        Returns DataFrame with columns:
            [date, regime, confidence, method]

        regime: "normal", "trending", "explosive", "mean_reverting"

        Args:
            prices: DataFrame with at least a price column (and optionally
                    a "date" column).
            method: Detection method. Currently "sadf" is supported.
            price_col: Name of the price column.

        Returns:
            pl.DataFrame with regime labels for each observation.
        """
        if price_col not in prices.columns:
            raise ValueError(f"Column '{price_col}' not found in DataFrame")

        raw = prices[price_col].drop_nulls().to_numpy().astype(np.float64)
        n = len(raw)

        if n < 20:
            raise ValueError(
                f"Need at least 20 observations for regime detection, got {n}"
            )

        # Determine date column
        has_date = "date" in prices.columns
        dates = (
            prices["date"].to_list()[:n]
            if has_date
            else list(range(n))
        )

        regimes: list[str] = []
        confidences: list[float] = []

        # --- Step 1: Check for explosive behavior via SADF ---
        try:
            sadf_result = self.sadf_test(
                prices, min_window=max(20, n // 5), price_col=price_col
            )
            sadf_stat = sadf_result["sadf_stat"]
            cv_95 = sadf_result["critical_values"]["95%"]
            cv_99 = sadf_result["critical_values"]["99%"]
        except (ValueError, Exception):
            sadf_stat = float("-inf")
            cv_95 = 1.0
            cv_99 = 1.9

        is_explosive = sadf_stat > cv_95

        # --- Step 2: Check stationarity ---
        try:
            adf_result = adf_test(pl.Series("p", raw), regression="c")
            is_stationary = adf_result["is_stationary"]
            adf_pval = adf_result["p_value"]
        except (ValueError, Exception):
            is_stationary = False
            adf_pval = 1.0

        # --- Step 3: Check trend via simple regression slope ---
        t_vals = np.arange(n, dtype=np.float64)
        x_trend = np.column_stack([t_vals, np.ones(n)])
        beta_trend, _, _, _ = np.linalg.lstsq(x_trend, raw, rcond=None)
        slope = beta_trend[0]
        # t-statistic of slope
        residuals_trend = raw - x_trend @ beta_trend
        sigma_trend = np.std(residuals_trend, ddof=2) if n > 2 else 1.0
        se_slope = sigma_trend / np.sqrt(np.sum((t_vals - t_vals.mean()) ** 2)) if sigma_trend > 0 else 1.0
        t_stat_slope = slope / se_slope if se_slope > 0 else 0.0
        is_trending = abs(t_stat_slope) > 2.0  # ~5% significance

        # --- Assign global regime ---
        if is_explosive:
            global_regime = "explosive"
            if sadf_stat > cv_99:
                global_confidence = 0.99
            elif sadf_stat > cv_95:
                global_confidence = 0.95
            else:
                global_confidence = 0.90
        elif is_stationary:
            global_regime = "mean_reverting"
            global_confidence = 1.0 - adf_pval
        elif is_trending:
            global_regime = "trending"
            # Confidence from t-statistic p-value
            trend_pval = 2.0 * (1.0 - scipy_stats.t.cdf(abs(t_stat_slope), df=n - 2))
            global_confidence = 1.0 - trend_pval
        else:
            global_regime = "normal"
            global_confidence = 0.5

        global_confidence = float(np.clip(global_confidence, 0.0, 1.0))

        for _ in range(n):
            regimes.append(global_regime)
            confidences.append(global_confidence)

        result_df = pl.DataFrame({
            "date": dates,
            "regime": regimes,
            "confidence": confidences,
            "method": [method] * n,
        })

        return result_df
