"""Fractional differentiation for stationarity with memory preservation.

Implements fixed-window and expanding-window fractional differentiation
from AFML Chapter 5 (Equations 5.1-5.6). The key insight: integer
differencing (d=1) achieves stationarity but destroys memory; fractional
d in (0,1) finds the sweet spot — stationary enough for ML, with maximum
memory retained.

Reference: Advances in Financial Machine Learning, Ch 5 — M. Lopez de Prado
"""

from __future__ import annotations

import numpy as np
import polars as pl

from analytics.statistics import adf_test
from core.features import BaseFeature, FeatureRegistry


class FractionalDifferentiator:
    """Fractionally differentiate a time series to achieve stationarity
    while preserving maximum memory.

    Reference: AFML Ch 5, Equations 5.1-5.6
    """

    @staticmethod
    def compute_weights(d: float, size: int, threshold: float = 1e-5) -> np.ndarray:
        """Compute weights w_k for the binomial expansion of (1-B)^d.

        w_0 = 1
        w_k = -w_{k-1} * (d - k + 1) / k,  for k >= 1

        Weights are truncated when |w_k| < threshold or k reaches size.

        Args:
            d: Fractional differencing order, typically in [0, 1].
            size: Maximum number of weights to compute.
            threshold: Stop when |w_k| drops below this value.

        Returns:
            1-D array of weights, length <= size.
        """
        weights = [1.0]
        for k in range(1, size):
            w_k = -weights[-1] * (d - k + 1) / k
            if abs(w_k) < threshold:
                break
            weights.append(w_k)
        return np.array(weights, dtype=np.float64)

    @staticmethod
    def frac_diff_fixed_window(
        series: pl.Series,
        d: float,
        window: int = 100,
    ) -> pl.Series:
        """Fixed-width window fractional differentiation (FFD).

        Applies the binomial weights over a fixed rolling window. This keeps
        computational cost constant per observation regardless of series length.

        Args:
            series: Price series (polars Series).
            d: Fractional differencing order in [0, 1].
            window: Rolling window width for weight application.

        Returns:
            Fractionally differenced series. First (window-1) values are null.
        """
        arr = series.to_numpy().astype(np.float64)
        n = len(arr)

        # Compute weights up to window size, no threshold cutoff for fixed window
        weights = np.array([1.0], dtype=np.float64)
        for k in range(1, window):
            w_k = -weights[-1] * (d - k + 1) / k
            weights = np.append(weights, w_k)

        w_len = len(weights)
        result = np.full(n, np.nan)

        for i in range(w_len - 1, n):
            segment = arr[i - w_len + 1 : i + 1]
            # Weights are applied in reverse: w_0 * x_t + w_1 * x_{t-1} + ...
            result[i] = np.dot(weights, segment[::-1])

        return pl.Series(series.name, result)

    @staticmethod
    def frac_diff_expanding(
        series: pl.Series,
        d: float,
        threshold: float = 1e-5,
    ) -> pl.Series:
        """Expanding window FFD with weight cutoff.

        Unlike fixed window, this uses all weights above the threshold,
        so the effective window grows until the weights decay below threshold.

        Args:
            series: Price series (polars Series).
            d: Fractional differencing order in [0, 1].
            threshold: Weight cutoff — stop including older observations
                when |w_k| < threshold.

        Returns:
            Fractionally differenced series. Initial values (before enough
            history is available) are null.
        """
        arr = series.to_numpy().astype(np.float64)
        n = len(arr)

        weights = FractionalDifferentiator.compute_weights(d, n, threshold)
        w_len = len(weights)

        result = np.full(n, np.nan)

        for i in range(w_len - 1, n):
            segment = arr[i - w_len + 1 : i + 1]
            result[i] = np.dot(weights, segment[::-1])

        return pl.Series(series.name, result)

    @staticmethod
    def find_min_d(
        series: pl.Series,
        max_d: float = 1.0,
        step: float = 0.05,
        significance: float = 0.05,
    ) -> float:
        """Find minimum d that makes the series stationary via ADF test.

        Grid search over d in [0, max_d] with the given step size.
        Returns the smallest d where ADF p-value < significance.

        Args:
            series: Price series (polars Series).
            max_d: Upper bound for d search.
            step: Step size for the grid search.
            significance: p-value threshold for stationarity.

        Returns:
            Minimum d value that achieves stationarity. Returns max_d if
            no d in the search range produces a stationary series.
        """
        d_values = np.arange(0, max_d + step / 2, step)

        for d in d_values:
            if d == 0.0:
                # Test original series
                try:
                    result = adf_test(series)
                    if result["p_value"] < significance:
                        return 0.0
                except ValueError:
                    continue
            else:
                diff_series = FractionalDifferentiator.frac_diff_fixed_window(
                    series, d, window=min(100, len(series)),
                )
                # Drop nulls and NaNs for ADF test
                clean = diff_series.drop_nulls().drop_nans()
                if len(clean) < 20:
                    continue
                try:
                    result = adf_test(clean)
                    if result["p_value"] < significance:
                        return round(float(d), 10)
                except ValueError:
                    continue

        return float(max_d)


@FeatureRegistry.register
class FracDiffFeature(BaseFeature):
    """Registry-compatible fractional differentiation feature.

    Automatically finds optimal d per ticker if d=None. Wraps
    FractionalDifferentiator for use in the feature pipeline.
    """

    def __init__(
        self,
        d: float | None = None,
        window: int = 100,
        price_col: str = "close",
    ) -> None:
        self._d = d
        self._window = window
        self._price_col = price_col

    @property
    def name(self) -> str:
        return f"frac_diff_{self._d or 'auto'}"

    @property
    def lookback_days(self) -> int:
        return self._window

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        """Compute fractionally differenced series.

        If d is None, find_min_d is called to auto-detect the optimal d.
        Then frac_diff_fixed_window is applied.

        Args:
            data: DataFrame with at least a price column (default "close").

        Returns:
            Input DataFrame with an additional "frac_diff" column.
        """
        price_series = data[self._price_col]

        if self._d is None:
            d = FractionalDifferentiator.find_min_d(price_series)
        else:
            d = self._d

        diff_series = FractionalDifferentiator.frac_diff_fixed_window(
            price_series, d, window=self._window,
        )

        return data.with_columns(diff_series.alias("frac_diff"))
