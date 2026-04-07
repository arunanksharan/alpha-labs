"""Monte Carlo simulation for Value at Risk estimation.

Provides single-asset and multi-asset (portfolio) VaR via Monte Carlo
simulation, with support for multi-day horizons and stress testing.
"""

from __future__ import annotations

import numpy as np
import polars as pl


class MonteCarloVaR:
    """Monte Carlo simulation for Value at Risk estimation.

    Parameters
    ----------
    n_simulations : int
        Number of Monte Carlo paths to generate.
    seed : int | None
        Random seed for reproducibility.  Pass ``None`` for non-deterministic
        behaviour.
    """

    def __init__(self, n_simulations: int = 10_000, seed: int | None = None) -> None:
        self.n_simulations = n_simulations
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # Single-asset helpers
    # ------------------------------------------------------------------

    def simulate_returns(
        self,
        historical_returns: pl.Series,
        n_days: int = 1,
    ) -> np.ndarray:
        """Simulate future daily returns drawn from a fitted normal distribution.

        Parameters
        ----------
        historical_returns : pl.Series
            Observed daily returns used to calibrate the distribution.
        n_days : int
            Number of forward days to simulate per path.

        Returns
        -------
        np.ndarray
            Array of shape ``(n_simulations, n_days)`` with simulated daily
            returns.
        """
        r = historical_returns.drop_nulls().to_numpy().astype(np.float64)
        mu = float(np.mean(r))
        sigma = float(np.std(r, ddof=1))

        simulated: np.ndarray = self._rng.normal(
            loc=mu,
            scale=sigma,
            size=(self.n_simulations, n_days),
        )
        return simulated

    def compute_var(
        self,
        historical_returns: pl.Series,
        confidence: float = 0.95,
        n_days: int = 1,
    ) -> float:
        """Compute Value at Risk via Monte Carlo simulation.

        The total return for each simulation is the compounded product of
        daily returns over *n_days*.

        Parameters
        ----------
        historical_returns : pl.Series
            Observed daily returns.
        confidence : float
            Confidence level (e.g. 0.95 for 95 % VaR).
        n_days : int
            Holding-period horizon in trading days.

        Returns
        -------
        float
            The VaR estimate (a negative number for typical long portfolios).
        """
        sim = self.simulate_returns(historical_returns, n_days)
        total_returns: np.ndarray = np.prod(1.0 + sim, axis=1) - 1.0
        return float(np.percentile(total_returns, (1 - confidence) * 100))

    def compute_cvar(
        self,
        historical_returns: pl.Series,
        confidence: float = 0.95,
        n_days: int = 1,
    ) -> float:
        """Compute Conditional Value at Risk (Expected Shortfall).

        Returns the mean of all simulated total returns that fall at or below
        the VaR threshold.

        Parameters
        ----------
        historical_returns : pl.Series
            Observed daily returns.
        confidence : float
            Confidence level.
        n_days : int
            Holding-period horizon in trading days.

        Returns
        -------
        float
            The CVaR estimate (always <= VaR).
        """
        sim = self.simulate_returns(historical_returns, n_days)
        total_returns: np.ndarray = np.prod(1.0 + sim, axis=1) - 1.0
        var_threshold = float(np.percentile(total_returns, (1 - confidence) * 100))
        tail = total_returns[total_returns <= var_threshold]
        if len(tail) == 0:
            return var_threshold
        return float(np.mean(tail))

    # ------------------------------------------------------------------
    # Multi-asset portfolio
    # ------------------------------------------------------------------

    def portfolio_var(
        self,
        returns_dict: dict[str, pl.Series],
        weights: dict[str, float],
        confidence: float = 0.95,
        n_days: int = 1,
    ) -> float:
        """Compute portfolio VaR with correlated asset returns.

        Uses the Cholesky decomposition of the historical covariance matrix
        to generate correlated multivariate normal samples.

        Parameters
        ----------
        returns_dict : dict[str, pl.Series]
            Mapping of asset name to its historical daily return series.
        weights : dict[str, float]
            Portfolio weights keyed by asset name (must match *returns_dict*).
        confidence : float
            Confidence level.
        n_days : int
            Holding-period horizon in trading days.

        Returns
        -------
        float
            Portfolio VaR as a negative number for typical diversified
            portfolios.
        """
        assets = list(returns_dict.keys())
        n_assets = len(assets)

        # Align all series to the shortest length
        arrays = {
            name: series.drop_nulls().to_numpy().astype(np.float64)
            for name, series in returns_dict.items()
        }
        min_len = min(len(a) for a in arrays.values())
        aligned = np.column_stack([arrays[name][:min_len] for name in assets])

        means = np.mean(aligned, axis=0)
        cov_matrix = np.cov(aligned, rowvar=False, ddof=1)

        # Cholesky decomposition for correlated sampling
        chol = np.linalg.cholesky(cov_matrix)

        w = np.array([weights[name] for name in assets])

        portfolio_total_returns = np.empty(self.n_simulations)
        for i in range(self.n_simulations):
            # Simulate n_days of correlated daily returns
            z = self._rng.standard_normal((n_days, n_assets))
            daily_returns = means + z @ chol.T  # (n_days, n_assets)

            # Compound each asset over n_days, then weight
            asset_total = np.prod(1.0 + daily_returns, axis=0) - 1.0
            portfolio_total_returns[i] = float(np.dot(w, asset_total))

        return float(np.percentile(portfolio_total_returns, (1 - confidence) * 100))

    # ------------------------------------------------------------------
    # Stress testing
    # ------------------------------------------------------------------

    def stress_test(
        self,
        historical_returns: pl.Series,
        shock_multiplier: float = 2.0,
    ) -> dict[str, float]:
        """Compare normal and stressed VaR at 95 % confidence.

        The stressed scenario inflates the historical volatility by
        *shock_multiplier* while keeping the mean unchanged.

        Parameters
        ----------
        historical_returns : pl.Series
            Observed daily returns.
        shock_multiplier : float
            Factor applied to standard deviation for the stress scenario.

        Returns
        -------
        dict[str, float]
            ``{"normal_var": …, "stressed_var": …, "stress_ratio": …}``
        """
        r = historical_returns.drop_nulls().to_numpy().astype(np.float64)
        mu = float(np.mean(r))
        sigma = float(np.std(r, ddof=1))

        # Normal scenario
        normal_sim = self._rng.normal(mu, sigma, size=self.n_simulations)
        normal_var = float(np.percentile(normal_sim, 5))

        # Stressed scenario
        stressed_sim = self._rng.normal(mu, sigma * shock_multiplier, size=self.n_simulations)
        stressed_var = float(np.percentile(stressed_sim, 5))

        stress_ratio = stressed_var / normal_var if normal_var != 0.0 else float("inf")

        return {
            "normal_var": normal_var,
            "stressed_var": stressed_var,
            "stress_ratio": stress_ratio,
        }
