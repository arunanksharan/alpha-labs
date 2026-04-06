"""Returns and risk metrics calculator for financial time series.

All functions operate on polars DataFrames with schema:
    - date: Date or Datetime column
    - One or more numeric value columns (close, returns, etc.)

Convention: the first non-date column is treated as the value column
unless otherwise specified.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy import stats as scipy_stats


def _value_col(df: pl.DataFrame) -> str:
    non_date = [
        c for c in df.columns
        if df[c].dtype not in (pl.Date, pl.Datetime, pl.Utf8, pl.Categorical)
    ]
    if not non_date:
        raise ValueError("DataFrame contains no numeric columns")
    return non_date[0]


def _require_min_rows(df: pl.DataFrame, n: int, label: str) -> None:
    if len(df) < n:
        raise ValueError(f"{label} requires at least {n} rows, got {len(df)}")


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------

def compute_returns(prices: pl.DataFrame, method: str = "log") -> pl.DataFrame:
    _require_min_rows(prices, 2, "compute_returns")
    col = _value_col(prices)
    date_cols = [c for c in prices.columns if prices[c].dtype in (pl.Date, pl.Datetime)]

    if method == "log":
        returns = (prices[col].log() - prices[col].shift(1).log()).alias("returns")
    elif method == "simple":
        returns = ((prices[col] / prices[col].shift(1)) - 1.0).alias("returns")
    else:
        raise ValueError(f"method must be 'log' or 'simple', got '{method}'")

    result_cols = [prices[c] for c in date_cols] + [returns]
    return pl.DataFrame(result_cols).drop_nulls()


def compute_cumulative_returns(returns: pl.DataFrame) -> pl.DataFrame:
    _require_min_rows(returns, 1, "compute_cumulative_returns")
    col = _value_col(returns)
    date_cols = [c for c in returns.columns if returns[c].dtype in (pl.Date, pl.Datetime)]

    cumulative = ((1.0 + returns[col]).cum_prod() - 1.0).alias("cumulative_returns")
    result_cols = [returns[c] for c in date_cols] + [cumulative]
    return pl.DataFrame(result_cols)


def compute_drawdown(returns: pl.DataFrame) -> pl.DataFrame:
    _require_min_rows(returns, 1, "compute_drawdown")
    col = _value_col(returns)
    date_cols = [c for c in returns.columns if returns[c].dtype in (pl.Date, pl.Datetime)]

    wealth = (1.0 + returns[col]).cum_prod()
    running_max = wealth.cum_max()
    dd = ((wealth / running_max) - 1.0).alias("drawdown")
    max_dd = dd.cum_min().alias("max_drawdown")

    result_cols = [returns[c] for c in date_cols] + [dd, max_dd]
    return pl.DataFrame(result_cols)


# ---------------------------------------------------------------------------
# Volatility
# ---------------------------------------------------------------------------

def compute_volatility(
    returns: pl.DataFrame,
    window: int = 21,
    annualize: bool = True,
) -> pl.DataFrame:
    _require_min_rows(returns, window, "compute_volatility")
    col = _value_col(returns)
    date_cols = [c for c in returns.columns if returns[c].dtype in (pl.Date, pl.Datetime)]

    factor = np.sqrt(252) if annualize else 1.0
    vol = (returns[col].rolling_std(window_size=window) * factor).alias("volatility")

    result_cols = [returns[c] for c in date_cols] + [vol]
    return pl.DataFrame(result_cols)


# ---------------------------------------------------------------------------
# Risk-adjusted ratios
# ---------------------------------------------------------------------------

def compute_sharpe(
    returns: pl.DataFrame,
    risk_free_rate: float = 0.0,
    periods: int = 252,
) -> float:
    col = _value_col(returns)
    _require_min_rows(returns, 2, "compute_sharpe")
    r = returns[col].drop_nulls()
    daily_rf = risk_free_rate / periods
    excess = r - daily_rf
    mean_excess = excess.mean()
    std = excess.std()
    if std is None or std == 0.0:
        return 0.0
    return float(mean_excess / std * np.sqrt(periods))  # type: ignore[arg-type]


def compute_sortino(
    returns: pl.DataFrame,
    risk_free_rate: float = 0.0,
    periods: int = 252,
) -> float:
    col = _value_col(returns)
    _require_min_rows(returns, 2, "compute_sortino")
    r = returns[col].drop_nulls().to_numpy()
    daily_rf = risk_free_rate / periods
    excess = r - daily_rf
    downside = excess[excess < 0]
    if len(downside) == 0:
        return float("inf")
    downside_std = float(np.std(downside, ddof=1))
    if downside_std == 0.0:
        return 0.0
    return float(np.mean(excess) / downside_std * np.sqrt(periods))


def compute_max_drawdown(returns: pl.DataFrame) -> float:
    col = _value_col(returns)
    _require_min_rows(returns, 1, "compute_max_drawdown")
    wealth = (1.0 + returns[col]).cum_prod()
    running_max = wealth.cum_max()
    dd = wealth / running_max - 1.0
    return float(dd.min())  # type: ignore[arg-type]


def compute_calmar(returns: pl.DataFrame, periods: int = 252) -> float:
    col = _value_col(returns)
    _require_min_rows(returns, 2, "compute_calmar")
    ann_return = float(returns[col].mean()) * periods  # type: ignore[arg-type]
    mdd = compute_max_drawdown(returns)
    if mdd == 0.0:
        return float("inf") if ann_return > 0 else 0.0
    return float(ann_return / abs(mdd))


# ---------------------------------------------------------------------------
# Value at Risk / Conditional VaR
# ---------------------------------------------------------------------------

def compute_var(
    returns: pl.DataFrame,
    confidence: float = 0.95,
    method: str = "historical",
) -> float:
    col = _value_col(returns)
    _require_min_rows(returns, 2, "compute_var")
    r = returns[col].drop_nulls().to_numpy()

    if method == "historical":
        return float(np.percentile(r, (1 - confidence) * 100))

    if method == "parametric":
        mu, sigma = float(np.mean(r)), float(np.std(r, ddof=1))
        z = scipy_stats.norm.ppf(1 - confidence)
        return float(mu + z * sigma)

    if method == "cornish-fisher":
        mu = float(np.mean(r))
        sigma = float(np.std(r, ddof=1))
        s = float(scipy_stats.skew(r))
        k = float(scipy_stats.kurtosis(r))
        z = scipy_stats.norm.ppf(1 - confidence)
        z_cf = (
            z
            + (z**2 - 1) * s / 6
            + (z**3 - 3 * z) * k / 24
            - (2 * z**3 - 5 * z) * s**2 / 36
        )
        return float(mu + z_cf * sigma)

    raise ValueError(f"method must be 'historical', 'parametric', or 'cornish-fisher', got '{method}'")


def compute_cvar(returns: pl.DataFrame, confidence: float = 0.95) -> float:
    col = _value_col(returns)
    _require_min_rows(returns, 2, "compute_cvar")
    r = returns[col].drop_nulls().to_numpy()
    var_threshold = float(np.percentile(r, (1 - confidence) * 100))
    tail = r[r <= var_threshold]
    if len(tail) == 0:
        return var_threshold
    return float(np.mean(tail))


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------

def compute_correlation_matrix(returns_dict: dict[str, pl.DataFrame]) -> pl.DataFrame:
    if len(returns_dict) < 2:
        raise ValueError("Need at least 2 return series for a correlation matrix")

    names = list(returns_dict.keys())
    arrays: dict[str, np.ndarray] = {}
    for name, df in returns_dict.items():
        col = _value_col(df)
        arrays[name] = df[col].drop_nulls().to_numpy()

    min_len = min(len(a) for a in arrays.values())
    trimmed = {n: a[:min_len] for n, a in arrays.items()}
    mat = np.corrcoef(np.stack([trimmed[n] for n in names]))

    data: dict[str, list[float]] = {"ticker": names}
    for i, name in enumerate(names):
        data[name] = [float(mat[i, j]) for j in range(len(names))]
    return pl.DataFrame(data)


def compute_rolling_correlation(
    returns1: pl.DataFrame,
    returns2: pl.DataFrame,
    window: int = 63,
) -> pl.DataFrame:
    col1 = _value_col(returns1)
    col2 = _value_col(returns2)
    min_len = min(len(returns1), len(returns2))
    _require_min_rows(returns1, window, "compute_rolling_correlation")

    date_cols = [c for c in returns1.columns if returns1[c].dtype in (pl.Date, pl.Datetime)]

    r1 = returns1[col1][:min_len].to_numpy()
    r2 = returns2[col2][:min_len].to_numpy()

    corr = np.full(min_len, np.nan)
    for i in range(window - 1, min_len):
        x = r1[i - window + 1 : i + 1]
        y = r2[i - window + 1 : i + 1]
        if np.std(x) == 0 or np.std(y) == 0:
            corr[i] = 0.0
        else:
            corr[i] = float(np.corrcoef(x, y)[0, 1])

    result_cols: list[pl.Series] = []
    for c in date_cols:
        result_cols.append(returns1[c][:min_len])
    result_cols.append(pl.Series("rolling_correlation", corr))
    return pl.DataFrame(result_cols)


# ---------------------------------------------------------------------------
# CAPM metrics
# ---------------------------------------------------------------------------

def compute_beta(returns: pl.DataFrame, benchmark: pl.DataFrame) -> float:
    col_r = _value_col(returns)
    col_b = _value_col(benchmark)
    min_len = min(len(returns), len(benchmark))
    _require_min_rows(returns, 2, "compute_beta")

    r = returns[col_r][:min_len].drop_nulls().to_numpy()
    b = benchmark[col_b][:min_len].drop_nulls().to_numpy()
    min_len = min(len(r), len(b))
    r, b = r[:min_len], b[:min_len]

    cov = np.cov(r, b, ddof=1)
    var_b = cov[1, 1]
    if var_b == 0.0:
        return 0.0
    return float(cov[0, 1] / var_b)


def compute_alpha(
    returns: pl.DataFrame,
    benchmark: pl.DataFrame,
    risk_free_rate: float = 0.0,
) -> float:
    col_r = _value_col(returns)
    col_b = _value_col(benchmark)
    _require_min_rows(returns, 2, "compute_alpha")

    beta = compute_beta(returns, benchmark)
    min_len = min(len(returns), len(benchmark))
    r_mean = float(returns[col_r][:min_len].mean())  # type: ignore[arg-type]
    b_mean = float(benchmark[col_b][:min_len].mean())  # type: ignore[arg-type]
    daily_rf = risk_free_rate / 252
    return float((r_mean - daily_rf) - beta * (b_mean - daily_rf))


def compute_information_ratio(
    returns: pl.DataFrame,
    benchmark: pl.DataFrame,
) -> float:
    col_r = _value_col(returns)
    col_b = _value_col(benchmark)
    min_len = min(len(returns), len(benchmark))
    _require_min_rows(returns, 2, "compute_information_ratio")

    r = returns[col_r][:min_len].to_numpy()
    b = benchmark[col_b][:min_len].to_numpy()
    active = r - b
    te = float(np.std(active, ddof=1))
    if te == 0.0:
        return 0.0
    return float(np.mean(active) / te * np.sqrt(252))
