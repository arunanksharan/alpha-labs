"""Rolling z-score feature for mean-reversion signals."""

from __future__ import annotations

import polars as pl

from core.features import BaseFeature, FeatureRegistry


@FeatureRegistry.register
class ZScoreFeature(BaseFeature):
    """Rolling z-score of price relative to its recent distribution."""

    def __init__(self, window: int = 20, price_col: str = "close") -> None:
        self._window = window
        self._price_col = price_col

    @property
    def name(self) -> str:
        return f"zscore_{self._window}"

    @property
    def lookback_days(self) -> int:
        return self._window

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        price = pl.col(self._price_col)
        rolling_mean = price.rolling_mean(window_size=self._window)
        rolling_std = price.rolling_std(window_size=self._window)

        zscore = (
            pl.when(rolling_std == 0.0)
            .then(pl.lit(0.0))
            .otherwise((price - rolling_mean) / rolling_std)
        )

        return data.with_columns(zscore.alias("zscore"))
