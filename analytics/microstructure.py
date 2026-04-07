"""Market microstructure analytics.

Functions for computing execution benchmarks (VWAP, TWAP), spread
estimation, liquidity metrics, and price-impact coefficients on
polars DataFrames.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy import stats as scipy_stats


def vwap(
    prices: pl.DataFrame,
    volume_col: str = "volume",
    price_col: str = "close",
) -> pl.DataFrame:
    """Add a cumulative VWAP column.

    Parameters
    ----------
    prices : pl.DataFrame
        Must contain *price_col* and *volume_col* columns.
    volume_col : str
        Name of the volume column.
    price_col : str
        Name of the price column.

    Returns
    -------
    pl.DataFrame
        Original frame with an additional ``vwap`` column.
    """
    return prices.with_columns(
        (
            (pl.col(price_col) * pl.col(volume_col)).cum_sum()
            / pl.col(volume_col).cum_sum()
        ).alias("vwap")
    )


def twap(
    prices: pl.DataFrame,
    window: int = 20,
    price_col: str = "close",
) -> pl.DataFrame:
    """Add a rolling time-weighted average price column.

    Parameters
    ----------
    prices : pl.DataFrame
        Must contain *price_col*.
    window : int
        Rolling window size.
    price_col : str
        Name of the price column.

    Returns
    -------
    pl.DataFrame
        Original frame with an additional ``twap`` column.
    """
    return prices.with_columns(
        pl.col(price_col).rolling_mean(window_size=window).alias("twap")
    )


def bid_ask_spread_estimate(
    prices: pl.DataFrame,
    price_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
    window: int = 20,
) -> pl.DataFrame:
    """Estimate the bid-ask spread using Roll (1984) and Corwin-Schultz (2012).

    The final ``estimated_spread`` column is the average of both estimators
    where both are available (Roll may produce NaN when the autocovariance
    is positive).

    Parameters
    ----------
    prices : pl.DataFrame
        Must contain *price_col*, *high_col*, and *low_col*.
    price_col : str
        Name of the close-price column.
    high_col : str
        Name of the high-price column.
    low_col : str
        Name of the low-price column.
    window : int
        Rolling window for the Roll estimator covariance.

    Returns
    -------
    pl.DataFrame
        Original frame with ``roll_spread``, ``cs_spread``, and
        ``estimated_spread`` columns.
    """
    # --- Roll (1984) estimator ---
    # spread = 2 * sqrt( -Cov(dp_t, dp_{t-1}) )
    dp = prices[price_col].diff()
    dp_lag = dp.shift(1)
    dp_np = dp.to_numpy().astype(float)
    dp_lag_np = dp_lag.to_numpy().astype(float)

    roll_spread = np.full(len(prices), np.nan)
    for i in range(window, len(prices)):
        x = dp_np[i - window + 1 : i + 1]
        y = dp_lag_np[i - window + 1 : i + 1]
        mask = ~(np.isnan(x) | np.isnan(y))
        if mask.sum() < 3:
            continue
        cov = np.cov(x[mask], y[mask])[0, 1]
        if cov < 0:
            roll_spread[i] = 2.0 * np.sqrt(-cov)
        else:
            roll_spread[i] = 0.0

    # --- Corwin-Schultz (2012) high-low estimator ---
    high = prices[high_col].to_numpy().astype(float)
    low = prices[low_col].to_numpy().astype(float)

    beta = np.full(len(prices), np.nan)
    for i in range(1, len(prices)):
        h2 = max(high[i], high[i - 1])
        l2 = min(low[i], low[i - 1])
        beta_val = (np.log(high[i] / low[i])) ** 2 + (np.log(high[i - 1] / low[i - 1])) ** 2
        beta[i] = beta_val

    gamma = np.full(len(prices), np.nan)
    for i in range(1, len(prices)):
        h2 = max(high[i], high[i - 1])
        l2 = min(low[i], low[i - 1])
        if h2 > 0 and l2 > 0:
            gamma[i] = (np.log(h2 / l2)) ** 2

    k = 2.0 * np.sqrt(2.0) - 1.0
    cs_spread = np.full(len(prices), np.nan)
    for i in range(1, len(prices)):
        if np.isnan(beta[i]) or np.isnan(gamma[i]):
            continue
        alpha_num = np.sqrt(2.0 * beta[i]) - np.sqrt(beta[i])
        alpha_den = 3.0 - 2.0 * np.sqrt(2.0)
        alpha_term = alpha_num / alpha_den - np.sqrt(gamma[i] / alpha_den)
        if alpha_term > 0:
            # S = 2*(exp(alpha) - 1) / (1 + exp(alpha))
            exp_a = np.exp(alpha_term)
            cs_spread[i] = 2.0 * (exp_a - 1.0) / (1.0 + exp_a)
        else:
            cs_spread[i] = 0.0

    # Average both estimators where available
    estimated = np.where(
        np.isnan(roll_spread),
        cs_spread,
        np.where(np.isnan(cs_spread), roll_spread, (roll_spread + cs_spread) / 2.0),
    )

    return prices.with_columns(
        pl.Series("roll_spread", roll_spread),
        pl.Series("cs_spread", cs_spread),
        pl.Series("estimated_spread", estimated),
    )


def amihud_illiquidity(
    prices: pl.DataFrame,
    window: int = 20,
    return_col: str | None = None,
    price_col: str = "close",
    volume_col: str = "volume",
) -> pl.DataFrame:
    """Compute rolling Amihud (2002) illiquidity ratio.

    ``ILLIQ = mean(|r_t| / volume_t)`` over a rolling window.

    Parameters
    ----------
    prices : pl.DataFrame
        Must contain *price_col* and *volume_col*.
    window : int
        Rolling window size.
    return_col : str | None
        Pre-computed return column. If ``None``, simple returns are
        derived from *price_col*.
    price_col : str
        Name of the close-price column.
    volume_col : str
        Name of the volume column.

    Returns
    -------
    pl.DataFrame
        Original frame with an additional ``amihud`` column.
    """
    if return_col and return_col in prices.columns:
        ret = pl.col(return_col).abs()
    else:
        ret = (pl.col(price_col) / pl.col(price_col).shift(1) - 1.0).abs()

    return prices.with_columns(
        (ret / pl.col(volume_col))
        .rolling_mean(window_size=window)
        .alias("amihud")
    )


def kyle_lambda(
    prices: pl.DataFrame,
    price_col: str = "close",
    volume_col: str = "volume",
) -> float:
    """Estimate Kyle's lambda via OLS: dp = lambda * signed_volume + eps.

    Signed volume is approximated using the Lee-Ready tick rule
    (sign of the price change multiplied by volume).

    Parameters
    ----------
    prices : pl.DataFrame
        Must contain *price_col* and *volume_col*.
    price_col : str
        Name of the close-price column.
    volume_col : str
        Name of the volume column.

    Returns
    -------
    float
        Estimated lambda (price impact per unit signed volume).
    """
    close = prices[price_col].to_numpy().astype(float)
    volume = prices[volume_col].to_numpy().astype(float)

    dp = np.diff(close)
    # Lee-Ready tick rule: sign of price change as trade direction proxy
    sign = np.sign(dp)
    signed_vol = sign * volume[1:]

    # Remove NaN / zero observations
    mask = ~(np.isnan(dp) | np.isnan(signed_vol) | (signed_vol == 0))
    dp_clean = dp[mask]
    sv_clean = signed_vol[mask]

    if len(dp_clean) < 2:
        raise ValueError("Not enough observations for Kyle lambda regression")

    slope, _intercept, _r, _p, _se = scipy_stats.linregress(sv_clean, dp_clean)
    return float(slope)
