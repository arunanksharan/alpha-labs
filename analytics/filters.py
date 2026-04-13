"""Event-based sampling filters for financial time series.

Implements the CUSUM filter from AFML Chapter 2, Section 2.5.2.1.
Instead of sampling at fixed intervals (daily bars), these filters
detect structurally significant events — moments when cumulative
deviations from the mean exceed a threshold.

All functions operate on polars DataFrames with schema:
    - date: Date column
    - close: Float64 price column (or user-specified column name)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import polars as pl


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class EventFilter(ABC):
    """Base class for event-based sampling filters.

    Subclasses implement a `filter` method that takes a price DataFrame
    and returns a DataFrame containing only rows where a structural
    event was detected.
    """

    @abstractmethod
    def filter(self, prices: pl.DataFrame, **kwargs: object) -> pl.DataFrame:
        """Return DataFrame of event timestamps."""


# ---------------------------------------------------------------------------
# CUSUM Filter
# ---------------------------------------------------------------------------

class CUSUMFilter(EventFilter):
    """Symmetric CUSUM filter for event-based sampling.

    Instead of sampling at fixed intervals (daily), detect when
    cumulative deviations from the mean exceed a threshold.

    Reference: AFML Ch 2, Section 2.5.2.1

    The filter maintains two cumulative sums:
        S_t^+ = max(0, S_{t-1}^+ + (y_t - E[y_t] - h))  # positive deviation
        S_t^- = min(0, S_{t-1}^- + (y_t - E[y_t] + h))  # negative deviation

    An event is triggered when S_t^+ > h or S_t^- < -h.
    After an event, the cumulative sum resets to 0.
    """

    def __init__(
        self,
        threshold: float | None = None,
        vol_multiplier: float = 2.0,
    ) -> None:
        """
        Args:
            threshold: Fixed threshold h. If None, computed as
                vol_multiplier * std(returns) in the filter call.
            vol_multiplier: Multiplier for dynamic threshold
                (used when threshold is None, or in filter_dynamic).
        """
        if threshold is not None and threshold <= 0:
            raise ValueError(f"threshold must be positive, got {threshold}")
        if vol_multiplier <= 0:
            raise ValueError(f"vol_multiplier must be positive, got {vol_multiplier}")
        self.threshold = threshold
        self.vol_multiplier = vol_multiplier

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def filter(
        self,
        prices: pl.DataFrame,
        price_col: str = "close",
        **kwargs: object,
    ) -> pl.DataFrame:
        """Apply CUSUM filter to price series.

        Computes simple returns first, then applies the symmetric CUSUM
        on those returns using a fixed threshold.

        Args:
            prices: DataFrame with ``date`` and price columns.
            price_col: Name of the price column.

        Returns:
            DataFrame with columns [date, event_type, cumsum_value]
            containing only rows where an event was triggered.
            ``event_type`` is ``"positive"`` or ``"negative"``.
        """
        self._validate_input(prices, price_col)
        if len(prices) < 2:
            return self._empty_result()

        returns = self._compute_returns(prices, price_col)
        dates = prices["date"].to_list()[1:]  # returns are offset by 1

        threshold = self.threshold
        if threshold is None:
            std = float(np.std(returns, ddof=1))
            if std == 0.0:
                return self._empty_result()
            threshold = self.vol_multiplier * std

        return self._run_cusum(returns, dates, np.full(len(returns), threshold))

    def filter_dynamic(
        self,
        prices: pl.DataFrame,
        vol_window: int = 20,
        price_col: str = "close",
    ) -> pl.DataFrame:
        """CUSUM with threshold = vol_multiplier * rolling_vol.

        Adapts to changing volatility regimes: during calm markets the
        threshold shrinks so smaller moves are detected; during turbulent
        markets the threshold grows to filter noise.

        Args:
            prices: DataFrame with ``date`` and price columns.
            vol_window: Rolling window for volatility estimation.
            price_col: Name of the price column.

        Returns:
            DataFrame with columns [date, event_type, cumsum_value].
        """
        self._validate_input(prices, price_col)
        if len(prices) < 2:
            return self._empty_result()

        returns = self._compute_returns(prices, price_col)
        dates = prices["date"].to_list()[1:]

        if len(returns) < vol_window:
            # Not enough data for rolling vol — fall back to global vol
            std = float(np.std(returns, ddof=1))
            if std == 0.0:
                return self._empty_result()
            thresholds = np.full(len(returns), self.vol_multiplier * std)
        else:
            rolling_vol = self._rolling_std(returns, vol_window)
            # For indices before vol_window, use the first valid vol value
            first_valid = rolling_vol[vol_window - 1]
            rolling_vol[:vol_window - 1] = first_valid
            # Replace any zero vol with a small positive number to avoid
            # degenerate thresholds
            rolling_vol[rolling_vol == 0.0] = 1e-12
            thresholds = self.vol_multiplier * rolling_vol

        return self._run_cusum(returns, dates, thresholds)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_input(prices: pl.DataFrame, price_col: str) -> None:
        if "date" not in prices.columns:
            raise ValueError("prices DataFrame must contain a 'date' column")
        if price_col not in prices.columns:
            raise ValueError(
                f"prices DataFrame must contain a '{price_col}' column"
            )

    @staticmethod
    def _compute_returns(prices: pl.DataFrame, price_col: str) -> np.ndarray:
        p = prices[price_col].to_numpy().astype(np.float64)
        return p[1:] / p[:-1] - 1.0

    @staticmethod
    def _rolling_std(arr: np.ndarray, window: int) -> np.ndarray:
        """Compute rolling standard deviation with ddof=1."""
        n = len(arr)
        result = np.full(n, np.nan)
        for i in range(window - 1, n):
            result[i] = float(np.std(arr[i - window + 1 : i + 1], ddof=1))
        return result

    @staticmethod
    def _empty_result() -> pl.DataFrame:
        return pl.DataFrame(
            {
                "date": pl.Series([], dtype=pl.Date),
                "event_type": pl.Series([], dtype=pl.Utf8),
                "cumsum_value": pl.Series([], dtype=pl.Float64),
            }
        )

    @staticmethod
    def _run_cusum(
        returns: np.ndarray,
        dates: list,
        thresholds: np.ndarray,
    ) -> pl.DataFrame:
        """Core CUSUM loop.

        Maintains S+ and S- running sums.  When either breaches its
        threshold, an event is recorded and both sums reset to zero.
        """
        mean_ret = float(np.mean(returns))
        s_pos = 0.0
        s_neg = 0.0

        event_dates: list = []
        event_types: list[str] = []
        event_values: list[float] = []

        for i in range(len(returns)):
            h = thresholds[i]
            y = returns[i] - mean_ret

            s_pos = max(0.0, s_pos + y - h)
            s_neg = min(0.0, s_neg + y + h)

            if s_pos > h:
                event_dates.append(dates[i])
                event_types.append("positive")
                event_values.append(float(s_pos))
                s_pos = 0.0
                s_neg = 0.0
            elif s_neg < -h:
                event_dates.append(dates[i])
                event_types.append("negative")
                event_values.append(float(s_neg))
                s_pos = 0.0
                s_neg = 0.0

        if not event_dates:
            return CUSUMFilter._empty_result()

        return pl.DataFrame(
            {
                "date": pl.Series(event_dates, dtype=pl.Date),
                "event_type": pl.Series(event_types, dtype=pl.Utf8),
                "cumsum_value": pl.Series(event_values, dtype=pl.Float64),
            }
        )
