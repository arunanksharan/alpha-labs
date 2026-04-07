"""Execution algorithms for order slicing (VWAP, TWAP) and trade analysis.

Provides schedule-based execution plans that distribute a parent order across
time slots, plus implementation shortfall decomposition and Almgren-Chriss
optimal horizon estimation.
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
class ExecutionPlan:
    """A time-sliced execution schedule for a parent order."""

    algorithm: str
    total_quantity: float
    n_slices: int
    schedule: pl.DataFrame  # [time_slot, target_quantity, target_pct]
    estimated_cost_bps: float


# ---------------------------------------------------------------------------
# VWAP scheduling
# ---------------------------------------------------------------------------


def vwap_schedule(
    total_quantity: float,
    historical_volumes: pl.DataFrame,
    n_slices: int = 10,
    participation_rate: float = 0.10,
) -> ExecutionPlan:
    """Distribute an order across time slots proportional to historical volume.

    Args:
        total_quantity: Total shares to execute (positive = buy, negative = sell).
        historical_volumes: DataFrame with columns ``[time_slot, avg_volume]``.
            Each row represents one intraday time bucket (e.g., 10 half-hour
            intervals in a trading day).
        n_slices: Number of time slots to use.  If *historical_volumes* has
            fewer rows the schedule is truncated; if more the first *n_slices*
            rows are used.
        participation_rate: Assumed fraction of slot volume consumed by the
            order, used to estimate market impact cost.

    Returns:
        An :class:`ExecutionPlan` with quantities allocated to each slot in
        proportion to that slot's historical volume share.
    """
    if total_quantity == 0.0:
        empty = pl.DataFrame(
            {
                "time_slot": pl.Series([], dtype=pl.Int64),
                "target_quantity": pl.Series([], dtype=pl.Float64),
                "target_pct": pl.Series([], dtype=pl.Float64),
            }
        )
        return ExecutionPlan(
            algorithm="VWAP",
            total_quantity=0.0,
            n_slices=0,
            schedule=empty,
            estimated_cost_bps=0.0,
        )

    # Truncate / pad to n_slices
    vol_df = historical_volumes.head(n_slices)
    actual_slices = vol_df.height

    volumes = vol_df.get_column("avg_volume").to_numpy().astype(np.float64)
    total_volume = float(np.sum(volumes))

    if total_volume <= 0.0:
        # Fallback to equal weighting when no volume data is useful
        pcts = np.ones(actual_slices) / actual_slices
    else:
        pcts = volumes / total_volume

    quantities = pcts * total_quantity

    schedule = pl.DataFrame(
        {
            "time_slot": vol_df.get_column("time_slot").to_list()[:actual_slices],
            "target_quantity": quantities.tolist(),
            "target_pct": pcts.tolist(),
        }
    )

    # Estimated cost: weighted average participation rate per slot drives
    # temporary impact ~ sigma * sqrt(participation).  Use a simplified
    # aggregate: cost_bps ~ 10_000 * sum_i (pct_i * sqrt(q_i / (V_i * pr)))
    # with a normalising volatility assumption of 2% daily.
    daily_vol = 0.02
    cost_bps = 0.0
    abs_qty = abs(total_quantity)
    for i in range(actual_slices):
        slot_vol = float(volumes[i])
        slot_qty = abs(float(quantities[i]))
        if slot_vol > 0.0 and slot_qty > 0.0:
            pr = slot_qty / (slot_vol * participation_rate)
            cost_bps += (slot_qty / abs_qty) * daily_vol * math.sqrt(pr) * 10_000.0

    return ExecutionPlan(
        algorithm="VWAP",
        total_quantity=total_quantity,
        n_slices=actual_slices,
        schedule=schedule,
        estimated_cost_bps=round(cost_bps, 4),
    )


# ---------------------------------------------------------------------------
# TWAP scheduling
# ---------------------------------------------------------------------------


def twap_schedule(
    total_quantity: float,
    n_slices: int = 10,
) -> ExecutionPlan:
    """Distribute an order equally across *n_slices* time slots.

    Args:
        total_quantity: Total shares to execute.
        n_slices: Number of equal-sized time buckets.

    Returns:
        An :class:`ExecutionPlan` with uniform allocation.
    """
    if n_slices <= 0:
        raise ValueError("n_slices must be a positive integer")

    qty_per_slot = total_quantity / n_slices
    pct_per_slot = 1.0 / n_slices

    schedule = pl.DataFrame(
        {
            "time_slot": list(range(n_slices)),
            "target_quantity": [qty_per_slot] * n_slices,
            "target_pct": [pct_per_slot] * n_slices,
        }
    )

    # TWAP cost estimate: uniform participation across the day.
    # Assume daily volume = n_slices * some average slot volume.
    # Simplified: cost ~ sqrt(1 / n_slices) * base_impact_bps.
    base_impact_bps = 10.0  # baseline for single-shot execution
    cost_bps = base_impact_bps * math.sqrt(1.0 / n_slices)

    return ExecutionPlan(
        algorithm="TWAP",
        total_quantity=total_quantity,
        n_slices=n_slices,
        schedule=schedule,
        estimated_cost_bps=round(cost_bps, 4),
    )


# ---------------------------------------------------------------------------
# Implementation shortfall
# ---------------------------------------------------------------------------


def implementation_shortfall(
    target_price: float,
    execution_prices: pl.DataFrame,
) -> dict[str, float]:
    """Compute implementation shortfall and decompose into cost components.

    Args:
        target_price: Decision / arrival price at the time the order was decided.
        execution_prices: DataFrame with columns ``[time_slot, price, quantity]``
            where each row is one execution slice.

    Returns:
        Dictionary with keys:

        * ``total_is_bps`` -- total implementation shortfall in basis points.
        * ``delay_bps`` -- cost attributable to delay between decision and
          first execution.
        * ``impact_bps`` -- cost attributable to market impact (price drift
          during execution).
        * ``timing_bps`` -- residual timing cost (total - delay - impact).
    """
    if target_price <= 0.0:
        raise ValueError("target_price must be positive")

    if execution_prices.height == 0:
        return {
            "total_is_bps": 0.0,
            "delay_bps": 0.0,
            "impact_bps": 0.0,
            "timing_bps": 0.0,
        }

    prices = execution_prices.get_column("price").to_numpy().astype(np.float64)
    quantities = execution_prices.get_column("quantity").to_numpy().astype(np.float64)

    total_qty = float(np.sum(quantities))
    if total_qty == 0.0:
        return {
            "total_is_bps": 0.0,
            "delay_bps": 0.0,
            "impact_bps": 0.0,
            "timing_bps": 0.0,
        }

    # Volume-weighted average execution price
    executed_avg = float(np.sum(prices * quantities) / total_qty)

    # Total IS
    total_is = (executed_avg - target_price) / target_price
    total_is_bps = total_is * 10_000.0

    # Delay cost: first execution price vs. target
    first_price = float(prices[0])
    delay = (first_price - target_price) / target_price
    delay_bps = delay * 10_000.0

    # Market impact: last execution price vs. first execution price,
    # weighted by execution profile
    last_price = float(prices[-1])
    impact = (last_price - first_price) / target_price
    impact_bps = impact * 10_000.0

    # Timing cost: residual
    timing_bps = total_is_bps - delay_bps - impact_bps

    return {
        "total_is_bps": round(total_is_bps, 4),
        "delay_bps": round(delay_bps, 4),
        "impact_bps": round(impact_bps, 4),
        "timing_bps": round(timing_bps, 4),
    }


# ---------------------------------------------------------------------------
# Almgren-Chriss optimal execution horizon
# ---------------------------------------------------------------------------


def optimal_execution_horizon(
    total_quantity: float,
    daily_volume: float,
    volatility: float,
    urgency: float = 1.0,
) -> float:
    """Estimate the optimal execution horizon using the Almgren-Chriss framework.

    Balances market impact cost (favours slow execution) against timing risk /
    volatility cost (favours fast execution).

    The simplified formula used here is:

        T* = (eta * Q / (kappa * sigma^2)) ^ (1/3) / urgency

    where *eta* is a temporary impact coefficient proportional to
    ``sigma / sqrt(daily_volume)``, *kappa* is risk aversion (set to 1),
    *Q* is ``total_quantity``, and *sigma* is daily volatility.

    Args:
        total_quantity: Number of shares to execute (absolute value is used).
        daily_volume: Average daily traded volume in shares.
        volatility: Daily return volatility (e.g. 0.02 for 2%).
        urgency: Urgency multiplier (>1 = faster, <1 = slower).  Default 1.0.

    Returns:
        Optimal number of trading days to complete the order.

    Raises:
        ValueError: If *daily_volume* or *volatility* is non-positive, or
            *urgency* is non-positive.
    """
    if daily_volume <= 0.0:
        raise ValueError("daily_volume must be positive")
    if volatility <= 0.0:
        raise ValueError("volatility must be positive")
    if urgency <= 0.0:
        raise ValueError("urgency must be positive")

    q = abs(total_quantity)
    if q == 0.0:
        return 0.0

    # Temporary impact coefficient: eta ~ sigma / sqrt(V)
    eta = volatility / math.sqrt(daily_volume)

    # Risk aversion parameter (kappa).  Higher urgency -> higher kappa -> shorter T*.
    kappa = 1.0

    # T* = (eta * Q / (kappa * sigma^2)) ^ (1/3)
    sigma_sq = volatility ** 2
    numerator = eta * q
    denominator = kappa * sigma_sq

    if denominator <= 0.0:
        return 0.0

    t_star = (numerator / denominator) ** (1.0 / 3.0)

    # Adjust for urgency
    t_star = t_star / urgency

    # Floor at a fraction of a day
    return max(round(t_star, 4), 0.01)
