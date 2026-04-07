"""Options pricing, Greeks, and volatility surface analysis.

All functions operate on polars DataFrames with schema:
    - date: Date or Datetime column
    - One or more numeric value columns (close, returns, etc.)

Convention: the first non-date column is treated as the value column
unless otherwise specified.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from dataclasses import dataclass
from scipy import stats as scipy_stats


@dataclass
class OptionPrice:
    """Container for Black-Scholes pricing output and Greeks."""

    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    option_type: str  # "call" or "put"


def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Compute d1 in the Black-Scholes formula."""
    return (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def _d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Compute d2 in the Black-Scholes formula."""
    return _d1(S, K, T, r, sigma) - sigma * np.sqrt(T)


def black_scholes(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
) -> OptionPrice:
    """Price a European option and compute all Greeks via Black-Scholes.

    Parameters
    ----------
    S : float
        Spot price of the underlying.
    K : float
        Strike price.
    T : float
        Time to expiry in years.
    r : float
        Risk-free interest rate (annualised, continuously compounded).
    sigma : float
        Volatility of the underlying (annualised).
    option_type : str
        ``"call"`` or ``"put"``.

    Returns
    -------
    OptionPrice
        Dataclass with price, delta, gamma, vega, theta, rho.
    """
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type must be 'call' or 'put', got '{option_type}'")
    if T <= 0:
        raise ValueError("T must be positive")
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(S, K, T, r, sigma)

    n_d1 = scipy_stats.norm.cdf(d1)
    n_d2 = scipy_stats.norm.cdf(d2)
    n_neg_d1 = scipy_stats.norm.cdf(-d1)
    n_neg_d2 = scipy_stats.norm.cdf(-d2)
    pdf_d1: float = scipy_stats.norm.pdf(d1)

    discount = np.exp(-r * T)
    sqrt_T = np.sqrt(T)

    if option_type == "call":
        price = float(S * n_d1 - K * discount * n_d2)
        delta = float(n_d1)
        theta = float(
            -(S * pdf_d1 * sigma) / (2.0 * sqrt_T)
            - r * K * discount * n_d2
        )
        rho = float(K * T * discount * n_d2)
    else:
        price = float(K * discount * n_neg_d2 - S * n_neg_d1)
        delta = float(n_d1 - 1.0)
        theta = float(
            -(S * pdf_d1 * sigma) / (2.0 * sqrt_T)
            + r * K * discount * n_neg_d2
        )
        rho = float(-K * T * discount * n_neg_d2)

    # Greeks common to both call and put
    gamma = float(pdf_d1 / (S * sigma * sqrt_T))
    vega = float(S * pdf_d1 * sqrt_T)

    return OptionPrice(
        price=price,
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta=theta,
        rho=rho,
        option_type=option_type,
    )


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
    tol: float = 1e-6,
    max_iter: int = 100,
) -> float:
    """Solve for implied volatility using Newton-Raphson.

    Parameters
    ----------
    market_price : float
        Observed market price of the option.
    S, K, T, r : float
        Black-Scholes parameters (spot, strike, expiry, rate).
    option_type : str
        ``"call"`` or ``"put"``.
    tol : float
        Convergence tolerance on price difference.
    max_iter : int
        Maximum Newton-Raphson iterations.

    Returns
    -------
    float
        Implied volatility (annualised).

    Raises
    ------
    ValueError
        If the solver does not converge within *max_iter* iterations.
    """
    sigma = 0.3  # initial guess

    for _ in range(max_iter):
        result = black_scholes(S, K, T, r, sigma, option_type)
        diff = result.price - market_price

        if abs(diff) < tol:
            return sigma

        if result.vega < 1e-12:
            # vega too small — nudge sigma to avoid division by zero
            sigma *= 1.5
            continue

        sigma = sigma - diff / result.vega

        # Keep sigma in a reasonable range
        sigma = max(sigma, 1e-6)
        sigma = min(sigma, 10.0)

    raise ValueError(
        f"Implied volatility did not converge after {max_iter} iterations "
        f"(last sigma={sigma:.6f}, price diff={diff:.6e})"
    )


def vol_surface(
    strikes: list[float] | np.ndarray,
    expiries: list[float] | np.ndarray,
    market_prices: np.ndarray,
    S: float,
    r: float,
    option_type: str = "call",
) -> pl.DataFrame:
    """Build an implied-volatility surface from a grid of market prices.

    Parameters
    ----------
    strikes : array-like
        Strike prices (length *m*).
    expiries : array-like
        Times to expiry in years (length *n*).
    market_prices : np.ndarray
        Shape ``(m, n)`` matrix of observed option prices.
    S : float
        Current spot price.
    r : float
        Risk-free rate.
    option_type : str
        ``"call"`` or ``"put"``.

    Returns
    -------
    pl.DataFrame
        Columns: ``strike``, ``expiry``, ``iv``, ``moneyness``.
    """
    strikes_arr = np.asarray(strikes, dtype=float)
    expiries_arr = np.asarray(expiries, dtype=float)

    if market_prices.shape != (len(strikes_arr), len(expiries_arr)):
        raise ValueError(
            f"market_prices shape {market_prices.shape} does not match "
            f"({len(strikes_arr)}, {len(expiries_arr)})"
        )

    rows: list[dict[str, float]] = []
    for i, K in enumerate(strikes_arr):
        for j, T in enumerate(expiries_arr):
            price = float(market_prices[i, j])
            try:
                iv = implied_volatility(price, S, K, T, r, option_type)
            except ValueError:
                iv = float("nan")
            rows.append(
                {
                    "strike": K,
                    "expiry": T,
                    "iv": iv,
                    "moneyness": K / S,
                }
            )

    return pl.DataFrame(rows)


def garch_forecast(
    returns: pl.Series,
    p: int = 1,
    q: int = 1,
    horizon: int = 10,
) -> pl.DataFrame:
    """Forecast volatility using a GARCH(p, q) model.

    Parameters
    ----------
    returns : pl.Series
        Historical log-return series.
    p : int
        GARCH lag order.
    q : int
        ARCH lag order.
    horizon : int
        Number of periods to forecast forward.

    Returns
    -------
    pl.DataFrame
        Columns: ``step``, ``forecast_vol``, ``lower_ci``, ``upper_ci``.
    """
    from arch import arch_model  # type: ignore[import-untyped]

    ret_np = returns.to_numpy().astype(float)
    # arch expects returns scaled to percentage points
    ret_scaled = ret_np * 100.0

    model = arch_model(ret_scaled, vol="Garch", p=p, q=q, mean="Zero", rescale=False)
    fit = model.fit(disp="off")
    forecasts = fit.forecast(horizon=horizon)

    # Variance forecasts — shape (1, horizon) for the last observation
    variance = forecasts.variance.iloc[-1].values
    vol = np.sqrt(variance) / 100.0  # scale back

    # Approximate 95 % confidence interval (chi-squared-like scaling)
    lower = vol * 0.75
    upper = vol * 1.35

    return pl.DataFrame(
        {
            "step": list(range(1, horizon + 1)),
            "forecast_vol": vol.tolist(),
            "lower_ci": lower.tolist(),
            "upper_ci": upper.tolist(),
        }
    )
