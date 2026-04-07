"""Strategy combiner for merging signals from multiple strategies.

Provides weighted signal combination, correlation analysis between
strategies, optimal weight computation, and performance summaries.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import polars as pl

from analytics.returns import (
    compute_correlation_matrix,
    compute_max_drawdown,
    compute_sharpe,
    compute_sortino,
)
from core.strategies import Signal


class StrategyCombiner:
    """Combine signals from multiple strategies with configurable weights."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        """Initialise with optional strategy weights.

        Args:
            weights: Mapping of strategy name to weight.  ``None`` means
                equal-weight all strategies at combine time.
        """
        self.weights = weights

    # ------------------------------------------------------------------
    # Signal combination
    # ------------------------------------------------------------------

    def combine(
        self, strategy_signals: dict[str, list[Signal]]
    ) -> list[Signal]:
        """Merge signals from multiple strategies into a single list.

        For the same ``(date, ticker)`` pair appearing in multiple strategies
        the combined signal uses:
        - **direction**: weighted average of each strategy's direction.
        - **confidence**: maximum confidence across strategies.

        Args:
            strategy_signals: ``{"strategy_name": [Signal, ...]}``.

        Returns:
            Combined list of :class:`Signal` objects.
        """
        names = list(strategy_signals.keys())
        weights = self._resolve_weights(names)

        # Group signals by (date, ticker)
        grouped: dict[tuple[str, str], list[tuple[str, Signal]]] = defaultdict(list)
        for name, signals in strategy_signals.items():
            for sig in signals:
                grouped[(sig.date, sig.ticker)].append((name, sig))

        combined: list[Signal] = []
        for (dt, ticker), entries in grouped.items():
            if len(entries) == 1:
                strat_name, sig = entries[0]
                combined.append(
                    Signal(
                        ticker=ticker,
                        date=dt,
                        direction=sig.direction * weights[strat_name],
                        confidence=sig.confidence,
                        metadata={"strategies": [strat_name]},
                    )
                )
            else:
                # Weighted average direction
                total_weight = sum(weights[name] for name, _ in entries)
                if total_weight == 0:
                    direction = 0.0
                else:
                    direction = sum(
                        weights[name] * sig.direction for name, sig in entries
                    ) / total_weight
                # Max confidence
                confidence = max(sig.confidence for _, sig in entries)
                combined.append(
                    Signal(
                        ticker=ticker,
                        date=dt,
                        direction=direction,
                        confidence=confidence,
                        metadata={"strategies": [name for name, _ in entries]},
                    )
                )

        return combined

    # ------------------------------------------------------------------
    # Correlation analysis
    # ------------------------------------------------------------------

    def correlation_analysis(
        self, strategy_returns: dict[str, pl.DataFrame]
    ) -> pl.DataFrame:
        """Compute pairwise correlation between strategy return series.

        Args:
            strategy_returns: ``{"strategy_name": DataFrame}`` where each
                DataFrame has a numeric returns column.

        Returns:
            Correlation matrix as a :class:`polars.DataFrame`.
        """
        return compute_correlation_matrix(strategy_returns)

    # ------------------------------------------------------------------
    # Optimal weights
    # ------------------------------------------------------------------

    def optimal_weights(
        self,
        strategy_returns: dict[str, pl.DataFrame],
        method: str = "equal",
    ) -> dict[str, float]:
        """Compute optimal strategy weights.

        Args:
            strategy_returns: ``{"strategy_name": DataFrame}``.
            method: ``"equal"`` (1/N), ``"inverse_vol"``, or
                ``"sharpe_weighted"``.

        Returns:
            Mapping of strategy name to weight (sums to 1.0).
        """
        names = list(strategy_returns.keys())
        n = len(names)

        if method == "equal":
            w = 1.0 / n
            return {name: w for name in names}

        if method == "inverse_vol":
            vols: dict[str, float] = {}
            for name, df in strategy_returns.items():
                col = _value_col(df)
                vol = float(df[col].std())  # type: ignore[arg-type]
                vols[name] = vol if vol > 0 else 1e-10
            inv_vols = {name: 1.0 / v for name, v in vols.items()}
            total = sum(inv_vols.values())
            return {name: iv / total for name, iv in inv_vols.items()}

        if method == "sharpe_weighted":
            sharpes: dict[str, float] = {}
            for name, df in strategy_returns.items():
                sharpes[name] = compute_sharpe(df)
            # Only positive-Sharpe strategies participate
            positive = {n: s for n, s in sharpes.items() if s > 0}
            if not positive:
                # Fall back to equal weight
                w = 1.0 / n
                return {name: w for name in names}
            total = sum(positive.values())
            result: dict[str, float] = {}
            for name in names:
                if name in positive:
                    result[name] = positive[name] / total
                else:
                    result[name] = 0.0
            return result

        raise ValueError(
            f"method must be 'equal', 'inverse_vol', or 'sharpe_weighted', "
            f"got '{method}'"
        )

    # ------------------------------------------------------------------
    # Performance summary
    # ------------------------------------------------------------------

    def performance_summary(
        self, strategy_returns: dict[str, pl.DataFrame]
    ) -> pl.DataFrame:
        """Compute risk/return summary for each strategy.

        Returns:
            DataFrame: [strategy, sharpe, sortino, max_drawdown, ann_return].
        """
        rows: list[dict[str, object]] = []
        for name, df in strategy_returns.items():
            col = _value_col(df)
            ann_ret = float(df[col].mean()) * 252  # type: ignore[arg-type]
            rows.append(
                {
                    "strategy": name,
                    "sharpe": compute_sharpe(df),
                    "sortino": compute_sortino(df),
                    "max_drawdown": compute_max_drawdown(df),
                    "ann_return": ann_ret,
                }
            )
        return pl.DataFrame(rows)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_weights(self, names: list[str]) -> dict[str, float]:
        """Return normalised weights for the given strategy names."""
        if self.weights is None:
            w = 1.0 / len(names)
            return {n: w for n in names}
        # Use provided weights; missing strategies get 0
        raw = {n: self.weights.get(n, 0.0) for n in names}
        total = sum(raw.values())
        if total == 0:
            w = 1.0 / len(names)
            return {n: w for n in names}
        return {n: v / total for n, v in raw.items()}


def _value_col(df: pl.DataFrame) -> str:
    """Return the first numeric column (mirrors analytics.returns._value_col)."""
    non_date = [
        c
        for c in df.columns
        if df[c].dtype not in (pl.Date, pl.Datetime, pl.Utf8, pl.Categorical)
    ]
    if not non_date:
        raise ValueError("DataFrame contains no numeric columns")
    return non_date[0]
