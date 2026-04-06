"""Mean reversion strategy — single-asset and pairs trading modes.

Single-asset: trades z-score of a single ticker's price.
Pairs: trades spread z-score between two cointegrated tickers.

Uses analytics.statistics for cointegration validation and half-life estimation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import polars as pl

from core.strategies import BaseStrategy, Signal, StrategyRegistry
from features.technical.zscore import ZScoreFeature
from features.technical.spread import SpreadFeature
from analytics.statistics import (
    adf_test,
    engle_granger_cointegration,
    half_life_mean_reversion,
    hurst_exponent,
)

logger = logging.getLogger(__name__)


@dataclass
class PairValidation:
    """Result of pair cointegration validation."""

    is_valid: bool
    hedge_ratio: float
    half_life: float
    hurst: float
    adf_pvalue: float
    cointegration_pvalue: float
    rejection_reason: str | None = None


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy with single-asset and pairs modes.

    Parameters
    ----------
    mode:
        "single" for z-score on one ticker, "pairs" for spread trading.
    entry_threshold:
        Z-score magnitude to enter a position.
    exit_threshold:
        Z-score magnitude to exit (revert to flat). Default 0 = mean crossing.
    window:
        Rolling window for z-score. None = auto-detect from half-life.
    max_weight:
        Maximum portfolio weight per signal.
    ticker_a, ticker_b:
        Required for pairs mode.
    cointegration_pvalue:
        Maximum p-value for cointegration test to accept pair.
    min_half_life, max_half_life:
        Acceptable half-life range in days.
    """

    def __init__(
        self,
        mode: str = "single",
        entry_threshold: float = 2.0,
        exit_threshold: float = 0.0,
        window: int | None = None,
        max_weight: float = 1.0,
        ticker_a: str | None = None,
        ticker_b: str | None = None,
        cointegration_pvalue: float = 0.05,
        min_half_life: float = 1.0,
        max_half_life: float = 252.0,
    ) -> None:
        self._mode = mode
        self._entry_threshold = entry_threshold
        self._exit_threshold = exit_threshold
        self._window = window if window is not None else 20
        self._max_weight = max_weight
        self._ticker_a = ticker_a
        self._ticker_b = ticker_b
        self._cointegration_pvalue = cointegration_pvalue
        self._min_half_life = min_half_life
        self._max_half_life = max_half_life
        self._hedge_ratio: float | None = None
        self._pair_validation: PairValidation | None = None

    @property
    def name(self) -> str:
        return "mean_reversion"

    @property
    def required_features(self) -> list[str]:
        if self._mode == "single":
            return [f"zscore_{self._window}"]
        return [f"spread_{self._ticker_a}_{self._ticker_b}"]

    def validate_pair(
        self, prices_a: pl.Series, prices_b: pl.Series
    ) -> PairValidation:
        """Run cointegration checks on a candidate pair.

        Tests: Engle-Granger cointegration, half-life range, Hurst exponent.
        Populates internal state (hedge_ratio, window) if valid.
        """
        coint = engle_granger_cointegration(prices_a, prices_b)

        if not coint["is_cointegrated"] or coint["p_value"] > self._cointegration_pvalue:
            return PairValidation(
                is_valid=False,
                hedge_ratio=coint["hedge_ratio"],
                half_life=0.0,
                hurst=0.0,
                adf_pvalue=1.0,
                cointegration_pvalue=coint["p_value"],
                rejection_reason=f"Not cointegrated (p={coint['p_value']:.4f})",
            )

        hedge_ratio = coint["hedge_ratio"]
        spread = prices_a.to_numpy() - hedge_ratio * prices_b.to_numpy()
        spread_series = pl.Series("spread", spread.tolist())

        hl = half_life_mean_reversion(spread_series)
        if hl < self._min_half_life or hl > self._max_half_life:
            return PairValidation(
                is_valid=False,
                hedge_ratio=hedge_ratio,
                half_life=hl,
                hurst=0.0,
                adf_pvalue=coint["p_value"],
                cointegration_pvalue=coint["p_value"],
                rejection_reason=f"Half-life {hl:.1f} outside [{self._min_half_life}, {self._max_half_life}]",
            )

        h = hurst_exponent(spread_series)

        adf = adf_test(spread_series)

        self._hedge_ratio = hedge_ratio
        self._window = max(10, min(252, int(round(hl))))

        validation = PairValidation(
            is_valid=True,
            hedge_ratio=hedge_ratio,
            half_life=hl,
            hurst=h,
            adf_pvalue=adf["p_value"],
            cointegration_pvalue=coint["p_value"],
        )
        self._pair_validation = validation

        logger.info(
            "Pair validated: hedge_ratio=%.4f half_life=%.1f hurst=%.4f window=%d",
            hedge_ratio,
            hl,
            h,
            self._window,
        )
        return validation

    def compute_features(self, data: pl.DataFrame) -> pl.DataFrame:
        """Compute required features from raw price data.

        For single mode: expects DataFrame with 'date' and 'close' columns.
        For pairs mode: expects DataFrame with 'date', 'close_a', 'close_b' columns.
        """
        if self._mode == "single":
            feature = ZScoreFeature(window=self._window)
            return feature.compute(data)

        if self._hedge_ratio is None:
            raise ValueError(
                "Call validate_pair() before compute_features() in pairs mode"
            )
        feature = SpreadFeature(
            ticker_a=self._ticker_a or "",
            ticker_b=self._ticker_b or "",
            hedge_ratio=self._hedge_ratio,
            window=self._window,
        )
        return feature.compute(data)

    def generate_signals(self, features: pl.DataFrame) -> list[Signal]:
        """Generate trading signals from features DataFrame.

        For single mode: features must have 'date', 'ticker', 'zscore' columns.
        For pairs mode: features must have 'date', 'spread_zscore' column.
        """
        z_col = "zscore" if self._mode == "single" else "spread_zscore"

        if z_col not in features.columns:
            raise ValueError(f"Missing required column '{z_col}' in features DataFrame")

        if "date" not in features.columns:
            raise ValueError("Missing required column 'date' in features DataFrame")

        signals: list[Signal] = []

        for row in features.iter_rows(named=True):
            z = row[z_col]
            if z is None:
                continue

            date_val = row["date"]
            date_str = str(date_val)

            if self._mode == "single":
                ticker = row.get("ticker", "UNKNOWN")
            else:
                ticker = f"{self._ticker_a}/{self._ticker_b}"

            if z < -self._entry_threshold:
                signals.append(Signal(
                    ticker=ticker,
                    date=date_str,
                    direction=1.0,
                    confidence=min(abs(z) / 4.0, 1.0),
                    metadata={"zscore": z, "action": "enter_long"},
                ))
            elif z > self._entry_threshold:
                signals.append(Signal(
                    ticker=ticker,
                    date=date_str,
                    direction=-1.0,
                    confidence=min(abs(z) / 4.0, 1.0),
                    metadata={"zscore": z, "action": "enter_short"},
                ))
            elif abs(z) <= self._exit_threshold:
                signals.append(Signal(
                    ticker=ticker,
                    date=date_str,
                    direction=0.0,
                    confidence=1.0,
                    metadata={"zscore": z, "action": "exit"},
                ))

        return signals

    def get_positions(
        self, signals: list[Signal], capital: float
    ) -> pl.DataFrame:
        """Convert signals to target positions.

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

        rows: list[dict] = []
        for sig in signals:
            weight = sig.direction * sig.confidence * self._max_weight
            value = abs(weight) * capital

            if self._mode == "pairs" and "/" in sig.ticker:
                parts = sig.ticker.split("/")
                rows.append({
                    "ticker": parts[0],
                    "weight": weight,
                    "target_shares": 0.0,
                    "target_value": value / 2,
                })
                rows.append({
                    "ticker": parts[1],
                    "weight": -weight,
                    "target_shares": 0.0,
                    "target_value": value / 2,
                })
            else:
                rows.append({
                    "ticker": sig.ticker,
                    "weight": weight,
                    "target_shares": 0.0,
                    "target_value": value,
                })

        return pl.DataFrame(rows)


StrategyRegistry.register(MeanReversionStrategy)
