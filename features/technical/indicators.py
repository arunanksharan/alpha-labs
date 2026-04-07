"""Technical analysis indicators built on pure polars expressions.

Each class implements BaseFeature and computes indicators from scratch
(no ta-lib dependency). All computations use polars column expressions
for vectorised, zero-copy performance.
"""

from __future__ import annotations

import polars as pl

from core.features import BaseFeature, FeatureRegistry


# ---------------------------------------------------------------------------
# RSI  (Relative Strength Index)
# ---------------------------------------------------------------------------


class RSIFeature(BaseFeature):
    """Wilder's RSI using exponential (EWM) smoothing of gains/losses."""

    def __init__(self, period: int = 14, price_col: str = "close") -> None:
        self._period = period
        self._price_col = price_col

    @property
    def name(self) -> str:
        return f"rsi_{self._period}"

    @property
    def lookback_days(self) -> int:
        return self._period + 1

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        price = pl.col(self._price_col)
        change = price.diff()

        gain = pl.when(change > 0).then(change).otherwise(pl.lit(0.0))
        loss = pl.when(change < 0).then(-change).otherwise(pl.lit(0.0))

        # Wilder's smoothing is equivalent to EWM with span = 2*period - 1
        # which gives alpha = 1/period.  Polars ewm_mean(span=...) uses
        # alpha = 2/(span+1), so we need span = 2*period - 1.
        span = 2 * self._period - 1

        avg_gain = gain.ewm_mean(span=span, ignore_nulls=True, min_samples=self._period)
        avg_loss = loss.ewm_mean(span=span, ignore_nulls=True, min_samples=self._period)

        rs = avg_gain / avg_loss
        rsi = pl.when(avg_loss == 0.0).then(pl.lit(100.0)).otherwise(
            pl.lit(100.0) - pl.lit(100.0) / (pl.lit(1.0) + rs)
        )

        return data.with_columns(rsi.alias("rsi"))


# ---------------------------------------------------------------------------
# MACD  (Moving Average Convergence Divergence)
# ---------------------------------------------------------------------------


class MACDFeature(BaseFeature):
    """Classic MACD with signal line and histogram."""

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        price_col: str = "close",
    ) -> None:
        self._fast = fast
        self._slow = slow
        self._signal = signal
        self._price_col = price_col

    @property
    def name(self) -> str:
        return f"macd_{self._fast}_{self._slow}_{self._signal}"

    @property
    def lookback_days(self) -> int:
        return self._slow + self._signal

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        price = pl.col(self._price_col)

        ema_fast = price.ewm_mean(span=self._fast, ignore_nulls=True, min_samples=self._fast)
        ema_slow = price.ewm_mean(span=self._slow, ignore_nulls=True, min_samples=self._slow)

        # Step 1: compute MACD line
        data = data.with_columns((ema_fast - ema_slow).alias("macd"))

        # Step 2: signal line = EMA of MACD line
        macd_col = pl.col("macd")
        signal_line = macd_col.ewm_mean(
            span=self._signal, ignore_nulls=True, min_samples=self._signal
        )

        data = data.with_columns(signal_line.alias("macd_signal"))

        # Step 3: histogram
        data = data.with_columns(
            (pl.col("macd") - pl.col("macd_signal")).alias("macd_histogram")
        )

        return data


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------


class BollingerBandsFeature(BaseFeature):
    """Bollinger Bands with %B and bandwidth."""

    def __init__(
        self, window: int = 20, num_std: float = 2.0, price_col: str = "close"
    ) -> None:
        self._window = window
        self._num_std = num_std
        self._price_col = price_col

    @property
    def name(self) -> str:
        return f"bollinger_{self._window}"

    @property
    def lookback_days(self) -> int:
        return self._window

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        price = pl.col(self._price_col)

        middle = price.rolling_mean(window_size=self._window)
        rolling_std = price.rolling_std(window_size=self._window)

        upper = middle + pl.lit(self._num_std) * rolling_std
        lower = middle - pl.lit(self._num_std) * rolling_std

        band_width = upper - lower

        pct_b = (
            pl.when(band_width == 0.0)
            .then(pl.lit(0.5))
            .otherwise((price - lower) / band_width)
        )

        bandwidth = (
            pl.when(middle == 0.0)
            .then(pl.lit(0.0))
            .otherwise(band_width / middle)
        )

        return data.with_columns(
            upper.alias("bb_upper"),
            lower.alias("bb_lower"),
            middle.alias("bb_middle"),
            pct_b.alias("bb_pct_b"),
            bandwidth.alias("bb_bandwidth"),
        )


# ---------------------------------------------------------------------------
# ATR  (Average True Range)
# ---------------------------------------------------------------------------


class ATRFeature(BaseFeature):
    """Average True Range using EMA smoothing of true range."""

    def __init__(self, period: int = 14) -> None:
        self._period = period

    @property
    def name(self) -> str:
        return f"atr_{self._period}"

    @property
    def lookback_days(self) -> int:
        return self._period + 1

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        high = pl.col("high")
        low = pl.col("low")
        prev_close = pl.col("close").shift(1)

        hl = high - low
        hpc = (high - prev_close).abs()
        lpc = (low - prev_close).abs()

        # True range = max of three ranges.  Use nested pl.max_horizontal.
        true_range = pl.max_horizontal(hl, hpc, lpc)

        data = data.with_columns(true_range.alias("true_range"))

        # ATR = EMA of true range (Wilder smoothing)
        span = 2 * self._period - 1
        atr = (
            pl.col("true_range")
            .ewm_mean(span=span, ignore_nulls=True, min_samples=self._period)
        )

        return data.with_columns(atr.alias("atr"))


# ---------------------------------------------------------------------------
# OBV  (On-Balance Volume)
# ---------------------------------------------------------------------------


class OBVFeature(BaseFeature):
    """On-Balance Volume: cumulative volume weighted by price direction."""

    def __init__(self, price_col: str = "close") -> None:
        self._price_col = price_col

    @property
    def name(self) -> str:
        return "obv"

    @property
    def lookback_days(self) -> int:
        return 2

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        price = pl.col(self._price_col)
        change = price.diff()

        sign = (
            pl.when(change > 0)
            .then(pl.lit(1.0))
            .when(change < 0)
            .then(pl.lit(-1.0))
            .otherwise(pl.lit(0.0))
        )

        obv = (pl.col("volume") * sign).cum_sum()

        return data.with_columns(obv.alias("obv"))


# ---------------------------------------------------------------------------
# Registry (default-parameter instances)
# ---------------------------------------------------------------------------

FeatureRegistry.register(RSIFeature)
FeatureRegistry.register(MACDFeature)
FeatureRegistry.register(BollingerBandsFeature)
FeatureRegistry.register(ATRFeature)
FeatureRegistry.register(OBVFeature)
