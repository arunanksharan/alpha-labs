"""Pairs trading spread feature for cointegration-based strategies."""

from __future__ import annotations

import polars as pl

from core.features import BaseFeature


class SpreadFeature(BaseFeature):
    """Spread and z-score between two cointegrated assets."""

    def __init__(
        self,
        ticker_a: str,
        ticker_b: str,
        hedge_ratio: float,
        window: int = 20,
    ) -> None:
        self._ticker_a = ticker_a
        self._ticker_b = ticker_b
        self._hedge_ratio = hedge_ratio
        self._window = window

    @property
    def name(self) -> str:
        return f"spread_{self._ticker_a}_{self._ticker_b}"

    @property
    def lookback_days(self) -> int:
        return self._window

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        spread = pl.col("close_a") - pl.lit(self._hedge_ratio) * pl.col("close_b")
        rolling_mean = spread.rolling_mean(window_size=self._window)
        rolling_std = spread.rolling_std(window_size=self._window)

        spread_zscore = (
            pl.when(rolling_std == 0.0)
            .then(pl.lit(0.0))
            .otherwise((spread - rolling_mean) / rolling_std)
        )

        return data.with_columns(
            spread.alias("spread"),
            spread_zscore.alias("spread_zscore"),
        )
