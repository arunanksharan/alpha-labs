"""Realistic execution cost modelling for backtests.

Models commission, slippage, and market impact (Almgren-Chriss) to produce
more honest backtest returns.  Also provides turnover computation and
capacity estimation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import polars as pl


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ExecutionCost:
    """Breakdown of execution costs for a single trade."""

    commission: float
    slippage: float
    market_impact: float
    total: float


# ---------------------------------------------------------------------------
# Execution model
# ---------------------------------------------------------------------------


class ExecutionModel:
    """Model realistic execution costs and market impact.

    Combines fixed commission, half-spread slippage, and a simplified
    Almgren-Chriss temporary market impact estimate.

    Args:
        commission_bps: Commission in basis points (10 = 0.10%).
        spread_bps: Half-spread in basis points (5 = 0.05%).
        market_impact_bps: Additional fixed impact (default 0, computed dynamically).
        participation_rate: Fraction of daily volume consumed by the trade.
    """

    def __init__(
        self,
        commission_bps: float = 10.0,
        spread_bps: float = 5.0,
        market_impact_bps: float = 0.0,
        participation_rate: float = 0.10,
    ) -> None:
        self.commission_bps = commission_bps
        self.spread_bps = spread_bps
        self.market_impact_bps = market_impact_bps
        self.participation_rate = participation_rate

    # ------------------------------------------------------------------
    # Core cost computation
    # ------------------------------------------------------------------

    def compute_costs(
        self,
        trade_value: float,
        daily_volume: float = 1e7,
        volatility: float = 0.02,
    ) -> ExecutionCost:
        """Compute all execution costs for a single trade.

        Args:
            trade_value: Absolute dollar value of the trade.
            daily_volume: Average daily traded dollar volume.
            volatility: Daily return volatility of the instrument.

        Returns:
            ExecutionCost with commission, slippage, market impact, and total.
        """
        if trade_value <= 0.0:
            return ExecutionCost(
                commission=0.0,
                slippage=0.0,
                market_impact=0.0,
                total=0.0,
            )

        commission = trade_value * self.commission_bps / 10_000.0
        slippage = trade_value * self.spread_bps / 10_000.0

        # Almgren-Chriss temporary impact:
        #   impact = sigma * sqrt(trade_value / (V * participation_rate))
        denominator = daily_volume * self.participation_rate
        if denominator > 0:
            market_impact = volatility * math.sqrt(trade_value / denominator)
            # Convert to dollar terms
            market_impact = market_impact * trade_value
        else:
            market_impact = 0.0

        # Add any fixed impact overlay
        market_impact += trade_value * self.market_impact_bps / 10_000.0

        total = commission + slippage + market_impact

        return ExecutionCost(
            commission=commission,
            slippage=slippage,
            market_impact=market_impact,
            total=total,
        )

    # ------------------------------------------------------------------
    # Return adjustment
    # ------------------------------------------------------------------

    def adjust_returns(
        self,
        returns: pl.DataFrame,
        trades: pl.DataFrame,
        prices: pl.DataFrame,
    ) -> pl.DataFrame:
        """Subtract realistic execution costs from daily returns.

        Args:
            returns: DataFrame with columns [date, returns].
            trades: DataFrame with columns [date, ticker, side, price, quantity, pnl].
            prices: OHLCV DataFrame with columns [date, ticker, close, volume].

        Returns:
            Returns DataFrame with an additional ``adjusted_returns`` column.
        """
        # Compute daily cost per date
        trade_costs: dict[str, float] = {}

        if trades.height == 0:
            return returns.with_columns(
                pl.col("returns").alias("adjusted_returns")
            )

        # Join trades with volume from prices for market impact
        trades_with_vol = trades.join(
            prices.select(["date", "ticker", "volume"]),
            on=["date", "ticker"],
            how="left",
        )

        for row in trades_with_vol.iter_rows(named=True):
            trade_value = abs(row["price"] * row["quantity"])
            volume_dollars = row.get("volume", 1e7) or 1e7
            # Rough daily vol from price as proxy
            vol_estimate = 0.02
            cost = self.compute_costs(
                trade_value=trade_value,
                daily_volume=volume_dollars * row.get("price", 1.0),
                volatility=vol_estimate,
            )
            dt = str(row["date"])
            trade_costs[dt] = trade_costs.get(dt, 0.0) + cost.total

        # Build cost series aligned to returns
        dates = returns.get_column("date").cast(pl.Utf8).to_list()
        cost_series = [trade_costs.get(str(d), 0.0) for d in dates]

        # Approximate portfolio value for cost-to-return conversion
        # Use cumulative returns to estimate equity
        ret_vals = returns.get_column("returns").to_numpy()
        equity = np.cumprod(1.0 + ret_vals) * 100_000.0
        equity = np.maximum(equity, 1.0)  # safety floor

        cost_frac = np.array(cost_series) / equity

        return returns.with_columns(
            (pl.col("returns") - pl.Series("_cost", cost_frac)).alias(
                "adjusted_returns"
            )
        )

    # ------------------------------------------------------------------
    # Turnover
    # ------------------------------------------------------------------

    @staticmethod
    def compute_turnover(weights: pl.DataFrame) -> pl.DataFrame:
        """Compute daily portfolio turnover from weight changes.

        Args:
            weights: DataFrame with a ``date`` column and one column per
                     asset holding the portfolio weight (float).

        Returns:
            DataFrame with columns [date, turnover].
        """
        date_col = "date"
        asset_cols = [c for c in weights.columns if c != date_col]

        if not asset_cols or weights.height < 2:
            return pl.DataFrame(
                {"date": weights.get_column(date_col).to_list(), "turnover": [0.0] * weights.height}
            )

        # Compute absolute change for each asset column, sum across assets
        diff_exprs = [
            (pl.col(c) - pl.col(c).shift(1)).abs().alias(f"_d_{c}")
            for c in asset_cols
        ]

        diffs = weights.with_columns(diff_exprs)
        diff_cols = [f"_d_{c}" for c in asset_cols]

        turnover_expr = sum(pl.col(c) for c in diff_cols)

        result = diffs.select(
            pl.col(date_col),
            turnover_expr.alias("turnover"),
        ).with_columns(pl.col("turnover").fill_null(0.0))

        return result

    # ------------------------------------------------------------------
    # Capacity estimation
    # ------------------------------------------------------------------

    def capacity_estimate(
        self,
        strategy_returns: pl.DataFrame,
        volumes: pl.DataFrame,
    ) -> float:
        """Estimate maximum AUM before returns degrade significantly.

        Finds the AUM level at which market impact eats more than 20% of
        the strategy alpha (annualised excess return).

        Args:
            strategy_returns: DataFrame with columns [date, returns].
            volumes: DataFrame with columns [date, volume] (dollar volume).

        Returns:
            Estimated capacity in dollars.  Returns inf if impact is negligible.
        """
        ret_array = strategy_returns.get_column("returns").to_numpy()
        ann_return = float(np.mean(ret_array) * 252)

        if ann_return <= 0:
            return 0.0

        # Average daily dollar volume
        avg_volume = float(volumes.get_column("volume").mean())
        if avg_volume <= 0:
            return 0.0

        daily_vol = float(np.std(ret_array))
        if daily_vol < 1e-12:
            return float("inf")

        # Threshold: impact should be < 20% of alpha
        alpha_threshold = 0.20 * ann_return

        # Impact per year (approx 252 trades) as function of AUM:
        #   annual_impact(AUM) = 252 * sigma * sqrt(AUM / (V * pr)) * (AUM / AUM)
        # Simplification: assume each day we trade fraction ~turnover of AUM.
        # For a rough estimate, assume full AUM turnover = 1 per day.
        # impact_per_trade = sigma * sqrt(AUM / (V * pr))
        # annual_impact = 252 * impact_per_trade
        # Solve: 252 * sigma * sqrt(AUM / (V * pr)) = alpha_threshold
        #   AUM = (alpha_threshold / (252 * sigma))^2 * V * pr

        denominator = 252.0 * daily_vol
        if denominator < 1e-12:
            return float("inf")

        capacity = (alpha_threshold / denominator) ** 2 * avg_volume * self.participation_rate

        return float(capacity)
