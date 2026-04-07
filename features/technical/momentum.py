"""Cross-sectional momentum feature (Jegadeesh-Titman style).

Computes the classic 12-1 momentum factor: total return over the past
`lookback` days, skipping the most recent `skip_recent` days to avoid
the short-term reversal effect.

Reference: Jegadeesh & Titman (1993), "Returns to Buying Winners and
Selling Losers: Implications for Stock Market Efficiency."
"""

from __future__ import annotations

import polars as pl

from core.features import BaseFeature, FeatureRegistry


@FeatureRegistry.register
class MomentumFeature(BaseFeature):
    """Cross-sectional momentum: past return skipping recent period.

    Parameters
    ----------
    lookback:
        Total lookback window in trading days (default 252 ~ 1 year).
    skip_recent:
        Number of most-recent days to skip (default 21 ~ 1 month).
    price_col:
        Name of the price column to use.
    """

    def __init__(
        self,
        lookback: int = 252,
        skip_recent: int = 21,
        price_col: str = "close",
    ) -> None:
        self._lookback = lookback
        self._skip_recent = skip_recent
        self._price_col = price_col

    @property
    def name(self) -> str:
        return f"momentum_{self._lookback}_{self._skip_recent}"

    @property
    def lookback_days(self) -> int:
        return self._lookback

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        """Compute Jegadeesh-Titman momentum.

        Formula: (price[t - skip_recent] / price[t - lookback]) - 1

        Uses polars ``shift()`` to lag prices, ensuring no look-ahead bias.
        """
        price = pl.col(self._price_col)

        price_recent = price.shift(self._skip_recent)
        price_past = price.shift(self._lookback)

        momentum = (price_recent / price_past) - 1.0

        return data.with_columns(momentum.alias("momentum"))
