"""Fama-French factor model for strategy attribution and analysis.

Provides multi-factor regression, rolling exposure estimation,
information coefficient computation, and return decomposition.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
from scipy import stats as scipy_stats


_FACTOR_COLS_3 = ["mkt_rf", "smb", "hml"]
_FACTOR_COLS_5 = ["mkt_rf", "smb", "hml", "rmw", "cma"]


class FamaFrenchModel:
    """Fama-French factor model for strategy attribution."""

    def __init__(self, n_factors: int = 3) -> None:
        """Initialise with 3 or 5 factors.

        Args:
            n_factors: 3 (market, SMB, HML) or 5 (+ RMW, CMA).
        """
        if n_factors not in (3, 5):
            raise ValueError(f"n_factors must be 3 or 5, got {n_factors}")
        self.n_factors = n_factors
        self.factor_names: list[str] = (
            list(_FACTOR_COLS_5) if n_factors == 5 else list(_FACTOR_COLS_3)
        )

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_factors(self, start: str, end: str) -> pl.DataFrame:
        """Return synthetic factor returns for testing.

        Generates reproducible daily factor data between *start* and *end*
        (inclusive, format ``YYYY-MM-DD``).  Real Kenneth French data can be
        plugged in later by replacing this method.

        Returns:
            DataFrame with columns: date, mkt_rf, smb, hml, [rmw, cma], rf.
        """
        start_dt = date.fromisoformat(start)
        end_dt = date.fromisoformat(end)

        dates: list[date] = []
        current = start_dt
        while current <= end_dt:
            if current.weekday() < 5:  # business days only
                dates.append(current)
            current += timedelta(days=1)

        n = len(dates)
        if n == 0:
            raise ValueError(f"No business days between {start} and {end}")

        rng = np.random.default_rng(seed=42)

        data: dict[str, object] = {"date": dates}
        # Market excess return: ~10 % annual, ~1 % daily vol
        data["mkt_rf"] = rng.normal(0.0004, 0.010, size=n).tolist()
        # SMB / HML: lower mean, lower vol
        data["smb"] = rng.normal(0.0001, 0.005, size=n).tolist()
        data["hml"] = rng.normal(0.0001, 0.005, size=n).tolist()

        if self.n_factors == 5:
            data["rmw"] = rng.normal(0.0001, 0.004, size=n).tolist()
            data["cma"] = rng.normal(0.0001, 0.003, size=n).tolist()

        # Risk-free rate (~4 % annualised)
        data["rf"] = [0.04 / 252] * n

        return pl.DataFrame(data).with_columns(pl.col("date").cast(pl.Date))

    # ------------------------------------------------------------------
    # Regression
    # ------------------------------------------------------------------

    def regression(
        self, returns: pl.Series, factors: pl.DataFrame
    ) -> dict[str, object]:
        """Run OLS: R_i - R_f = alpha + sum(beta_k * F_k) + epsilon.

        Args:
            returns: Strategy daily returns (same length as *factors*).
            factors: DataFrame produced by :meth:`load_factors`.

        Returns:
            dict with keys: alpha, alpha_tstat, betas, r_squared,
            residual_vol.
        """
        rf = factors["rf"].to_numpy()
        y = returns.to_numpy() - rf  # excess returns

        # Build factor matrix
        X_cols = [factors[f].to_numpy() for f in self.factor_names]
        X = np.column_stack([np.ones(len(y))] + X_cols)  # intercept first

        # OLS via least-squares
        coeffs, residuals, rank, sv = np.linalg.lstsq(X, y, rcond=None)

        alpha = float(coeffs[0])
        betas = {name: float(coeffs[i + 1]) for i, name in enumerate(self.factor_names)}

        y_hat = X @ coeffs
        resid = y - y_hat
        residual_vol = float(np.std(resid, ddof=len(coeffs)))

        # R-squared
        ss_res = float(np.sum(resid**2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # Alpha t-stat
        n_obs = len(y)
        dof = n_obs - X.shape[1]
        if dof > 0 and ss_res > 0:
            mse = ss_res / dof
            XtX_inv = np.linalg.inv(X.T @ X)
            se_alpha = float(np.sqrt(mse * XtX_inv[0, 0]))
            alpha_tstat = alpha / se_alpha if se_alpha > 0 else 0.0
        else:
            alpha_tstat = 0.0

        return {
            "alpha": alpha,
            "alpha_tstat": float(alpha_tstat),
            "betas": betas,
            "r_squared": r_squared,
            "residual_vol": residual_vol,
        }

    # ------------------------------------------------------------------
    # Attribution
    # ------------------------------------------------------------------

    def factor_attribution(
        self, returns: pl.Series, factors: pl.DataFrame
    ) -> pl.DataFrame:
        """Decompose strategy returns into factor contributions.

        Returns:
            DataFrame: [factor_name, beta, factor_return, contribution,
            pct_of_total].
        """
        reg = self.regression(returns, factors)
        betas: dict[str, float] = reg["betas"]  # type: ignore[assignment]

        rows: list[dict[str, object]] = []
        total_contribution = 0.0

        for name in self.factor_names:
            beta = betas[name]
            factor_return = float(factors[name].mean())  # type: ignore[arg-type]
            contribution = beta * factor_return
            total_contribution += contribution
            rows.append(
                {
                    "factor_name": name,
                    "beta": beta,
                    "factor_return": factor_return,
                    "contribution": contribution,
                    "pct_of_total": 0.0,  # placeholder
                }
            )

        # Add alpha row
        alpha: float = reg["alpha"]  # type: ignore[assignment]
        total_contribution += alpha
        rows.append(
            {
                "factor_name": "alpha",
                "beta": 0.0,
                "factor_return": 0.0,
                "contribution": alpha,
                "pct_of_total": 0.0,
            }
        )

        # Compute pct_of_total
        abs_total = sum(abs(r["contribution"]) for r in rows)  # type: ignore[arg-type]
        if abs_total > 0:
            for r in rows:
                r["pct_of_total"] = r["contribution"] / abs_total  # type: ignore[operator]

        return pl.DataFrame(rows)

    # ------------------------------------------------------------------
    # Information coefficient
    # ------------------------------------------------------------------

    def compute_information_coefficient(
        self, signals: pl.DataFrame, forward_returns: pl.DataFrame
    ) -> float:
        """Compute mean IC (rank correlation of signal vs forward return).

        Args:
            signals: [date, ticker, signal_value]
            forward_returns: [date, ticker, forward_return]

        Returns:
            Average Spearman rank-correlation across dates.
        """
        merged = signals.join(forward_returns, on=["date", "ticker"], how="inner")

        ics: list[float] = []
        for dt in merged["date"].unique().sort().to_list():
            day = merged.filter(pl.col("date") == dt)
            if len(day) < 3:
                continue
            sig = day["signal_value"].to_numpy()
            fwd = day["forward_return"].to_numpy()
            corr, _ = scipy_stats.spearmanr(sig, fwd)
            if not np.isnan(corr):
                ics.append(float(corr))

        if not ics:
            return 0.0
        return float(np.mean(ics))

    # ------------------------------------------------------------------
    # Rolling exposure
    # ------------------------------------------------------------------

    def rolling_factor_exposure(
        self,
        returns: pl.Series,
        factors: pl.DataFrame,
        window: int = 63,
    ) -> pl.DataFrame:
        """Compute rolling regression betas over time.

        Args:
            returns: Strategy daily returns.
            factors: Factor DataFrame from :meth:`load_factors`.
            window: Rolling window size in trading days.

        Returns:
            DataFrame with date and one column per factor beta.
        """
        n = len(returns)
        if n < window:
            raise ValueError(
                f"Need at least {window} observations, got {n}"
            )

        rf = factors["rf"].to_numpy()
        y_full = returns.to_numpy() - rf
        factor_arrays = {f: factors[f].to_numpy() for f in self.factor_names}
        dates = factors["date"]

        # Pre-allocate
        beta_results: dict[str, list[float | None]] = {
            f: [None] * n for f in self.factor_names
        }
        valid_dates: list[date] = []
        out_betas: dict[str, list[float]] = {f: [] for f in self.factor_names}

        for i in range(window - 1, n):
            start_idx = i - window + 1
            y_win = y_full[start_idx : i + 1]
            X_cols = [factor_arrays[f][start_idx : i + 1] for f in self.factor_names]
            X = np.column_stack([np.ones(window)] + X_cols)

            coeffs, _, _, _ = np.linalg.lstsq(X, y_win, rcond=None)

            valid_dates.append(dates[i])
            for j, f in enumerate(self.factor_names):
                out_betas[f].append(float(coeffs[j + 1]))

        data: dict[str, object] = {"date": valid_dates}
        for f in self.factor_names:
            data[f"{f}_beta"] = out_betas[f]

        return pl.DataFrame(data)
