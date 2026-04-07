"""Cross-sectional momentum strategy — long winners, short losers.

Ranks the universe by momentum and goes long the top percentile while
shorting the bottom percentile.  Equal-weight within each leg.
"""

from __future__ import annotations

import logging

import polars as pl

from core.strategies import BaseStrategy, Signal, StrategyRegistry

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """Long/short momentum strategy based on cross-sectional ranking.

    Parameters
    ----------
    lookback:
        Momentum lookback in trading days.
    skip_recent:
        Days to skip for short-term reversal avoidance.
    top_pct:
        Fraction of the universe to go long (top momentum).
    bottom_pct:
        Fraction of the universe to go short (bottom momentum).
    max_weight:
        Maximum absolute weight per position.
    """

    def __init__(
        self,
        lookback: int = 252,
        skip_recent: int = 21,
        top_pct: float = 0.2,
        bottom_pct: float = 0.2,
        max_weight: float = 1.0,
    ) -> None:
        self._lookback = lookback
        self._skip_recent = skip_recent
        self._top_pct = top_pct
        self._bottom_pct = bottom_pct
        self._max_weight = max_weight

    @property
    def name(self) -> str:
        return "momentum"

    @property
    def required_features(self) -> list[str]:
        return [f"momentum_{self._lookback}_{self._skip_recent}"]

    def generate_signals(self, features: pl.DataFrame) -> list[Signal]:
        """Generate long/short signals from cross-sectional momentum ranks.

        Args:
            features: DataFrame with columns ``date``, ``ticker``, ``momentum``.

        Returns:
            List of Signal objects for tickers in the top and bottom buckets.
        """
        for col in ("date", "ticker", "momentum"):
            if col not in features.columns:
                raise ValueError(f"Missing required column '{col}' in features DataFrame")

        # Drop rows where momentum is null (warmup period).
        valid = features.filter(pl.col("momentum").is_not_null())

        signals: list[Signal] = []

        for date_val, group in valid.group_by("date"):
            n_tickers = len(group)
            if n_tickers < 2:
                continue

            # Rank tickers by momentum (ascending: rank 0 = lowest momentum).
            ranked = group.sort("momentum")
            n_long = max(1, int(n_tickers * self._top_pct))
            n_short = max(1, int(n_tickers * self._bottom_pct))

            date_str = str(date_val[0])

            # Compute median rank for confidence scaling.
            median_rank = (n_tickers - 1) / 2.0

            for i, row in enumerate(ranked.iter_rows(named=True)):
                ticker = row["ticker"]
                rank = i  # 0 = lowest momentum, n-1 = highest

                # Confidence: normalized distance from median (0 at median, 1 at extremes).
                confidence = abs(rank - median_rank) / median_rank if median_rank > 0 else 1.0
                confidence = min(confidence, 1.0)

                if rank >= n_tickers - n_long:
                    # Top bucket — long.
                    signals.append(Signal(
                        ticker=ticker,
                        date=date_str,
                        direction=1.0,
                        confidence=confidence,
                        metadata={"momentum": row["momentum"], "rank": rank},
                    ))
                elif rank < n_short:
                    # Bottom bucket — short.
                    signals.append(Signal(
                        ticker=ticker,
                        date=date_str,
                        direction=-1.0,
                        confidence=confidence,
                        metadata={"momentum": row["momentum"], "rank": rank},
                    ))

        return signals

    def get_positions(
        self, signals: list[Signal], capital: float
    ) -> pl.DataFrame:
        """Convert signals to equal-weight target positions within each leg.

        Returns DataFrame with columns: ticker, weight, target_shares, target_value.
        """
        if not signals:
            return pl.DataFrame(
                schema={
                    "ticker": pl.Utf8,
                    "weight": pl.Float64,
                    "target_shares": pl.Float64,
                    "target_value": pl.Float64,
                }
            )

        long_signals = [s for s in signals if s.direction > 0]
        short_signals = [s for s in signals if s.direction < 0]

        rows: list[dict] = []

        # Equal weight within each leg.
        if long_signals:
            weight_per_long = min(self._max_weight, 1.0 / len(long_signals))
            for sig in long_signals:
                value = weight_per_long * capital
                rows.append({
                    "ticker": sig.ticker,
                    "weight": weight_per_long,
                    "target_shares": 0.0,
                    "target_value": value,
                })

        if short_signals:
            weight_per_short = min(self._max_weight, 1.0 / len(short_signals))
            for sig in short_signals:
                value = weight_per_short * capital
                rows.append({
                    "ticker": sig.ticker,
                    "weight": -weight_per_short,
                    "target_shares": 0.0,
                    "target_value": value,
                })

        return pl.DataFrame(rows)


StrategyRegistry.register(MomentumStrategy)
