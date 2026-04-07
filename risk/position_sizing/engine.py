"""Position sizing engines for the quant research platform.

Provides multiple methods for computing position sizes:
- Equal weight
- Kelly criterion (fractional)
- Inverse volatility
- Risk parity (iterative)
- Volatility targeting
- Max drawdown sizing
"""

from __future__ import annotations

import numpy as np
import polars as pl

from config.settings import settings


class PositionSizer:
    """Compute position sizes using various methods.

    All sizing methods respect the max_position_pct constraint, ensuring
    no single position exceeds the configured maximum percentage of capital.
    """

    def __init__(self, max_position_pct: float | None = None) -> None:
        self._max_pct = max_position_pct or settings.risk.max_position_pct

    # ------------------------------------------------------------------
    # Equal weight
    # ------------------------------------------------------------------

    def equal_weight(self, n_positions: int, capital: float) -> list[float]:
        """Return equal dollar allocations across *n_positions*.

        Parameters
        ----------
        n_positions:
            Number of positions to allocate across.
        capital:
            Total capital available for allocation.

        Returns
        -------
        list[float]
            Dollar amounts for each position.
        """
        if n_positions <= 0:
            return []
        raw = capital / n_positions
        cap = self._max_pct * capital
        clamped = min(raw, cap)
        return [clamped] * n_positions

    # ------------------------------------------------------------------
    # Kelly criterion
    # ------------------------------------------------------------------

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float | None = None,
    ) -> float:
        """Compute fractional Kelly position weight.

        Full Kelly: ``f* = (p * b - q) / b`` where ``p`` = win_rate,
        ``q`` = 1 - p, ``b`` = avg_win / avg_loss.

        Parameters
        ----------
        win_rate:
            Probability of a winning trade (0-1).
        avg_win:
            Average dollar gain on a winning trade (positive).
        avg_loss:
            Average dollar loss on a losing trade (positive magnitude).
        fraction:
            Kelly fraction to apply (e.g. 0.25 for quarter-Kelly).
            Defaults to ``settings.risk.kelly_fraction``.

        Returns
        -------
        float
            Position weight as a fraction of capital, clamped to
            [0, max_position_pct].
        """
        if avg_loss == 0.0:
            return 0.0

        frac = fraction if fraction is not None else settings.risk.kelly_fraction
        p = win_rate
        q = 1.0 - p
        b = avg_win / avg_loss

        full_kelly = (p * b - q) / b
        scaled = full_kelly * frac

        return float(np.clip(scaled, 0.0, self._max_pct))

    # ------------------------------------------------------------------
    # Inverse volatility
    # ------------------------------------------------------------------

    def inverse_volatility(
        self,
        volatilities: list[float],
        capital: float,
    ) -> list[float]:
        """Weight positions inversely proportional to their volatility.

        Parameters
        ----------
        volatilities:
            Annualised volatilities for each asset (must be > 0).
        capital:
            Total capital available for allocation.

        Returns
        -------
        list[float]
            Dollar amounts per asset, each clamped to
            max_position_pct * capital.
        """
        if not volatilities:
            return []

        vols = np.array(volatilities, dtype=np.float64)
        if np.any(vols <= 0):
            raise ValueError("All volatilities must be strictly positive")

        inv = 1.0 / vols
        weights = inv / inv.sum()

        cap = self._max_pct * capital
        allocations = weights * capital
        return [float(min(a, cap)) for a in allocations]

    # ------------------------------------------------------------------
    # Risk parity (iterative)
    # ------------------------------------------------------------------

    def risk_parity(
        self,
        returns_matrix: pl.DataFrame,
        capital: float,
        target_vol: float = 0.10,
        n_iter: int = 50,
    ) -> list[float]:
        """Compute risk-parity weights via iterative rebalancing.

        Each asset contributes equally to total portfolio risk.

        Parameters
        ----------
        returns_matrix:
            A polars DataFrame whose numeric columns are asset return
            series (rows = time observations, columns = assets).
        capital:
            Total capital available.
        target_vol:
            Desired annualised portfolio volatility.
        n_iter:
            Number of optimisation iterations.

        Returns
        -------
        list[float]
            Dollar amounts per asset.
        """
        # Extract numeric columns only
        numeric_cols = [
            c for c in returns_matrix.columns
            if returns_matrix[c].dtype in (pl.Float32, pl.Float64, pl.Int64, pl.Int32)
        ]
        if not numeric_cols:
            raise ValueError("returns_matrix has no numeric columns")

        mat = returns_matrix.select(numeric_cols).to_numpy()
        n_assets = mat.shape[1]

        # Annualised covariance matrix
        cov = np.cov(mat, rowvar=False) * 252
        # Handle single-asset edge case: np.cov returns a scalar
        if cov.ndim == 0:
            cov = np.array([[float(cov)]])

        # Iterative risk-parity
        w = np.ones(n_assets) / n_assets
        for _ in range(n_iter):
            marginal_risk = cov @ w  # (n,)
            # Guard against zero marginal risk
            marginal_risk = np.maximum(marginal_risk, 1e-12)
            w = 1.0 / marginal_risk
            w = w / w.sum()

        # Scale to target volatility
        port_var = float(w @ cov @ w)
        port_vol = np.sqrt(port_var) if port_var > 0 else 1e-12
        scale = target_vol / port_vol
        w = w * scale

        # Convert to dollar allocations and clamp
        cap = self._max_pct * capital
        allocations = w * capital
        return [float(min(a, cap)) for a in allocations]

    # ------------------------------------------------------------------
    # Volatility targeting
    # ------------------------------------------------------------------

    def volatility_targeting(
        self,
        current_vol: float,
        target_vol: float,
        current_weight: float,
    ) -> float:
        """Scale a position to achieve a target volatility contribution.

        Parameters
        ----------
        current_vol:
            Current annualised volatility of the position / asset.
        target_vol:
            Desired annualised volatility level.
        current_weight:
            Current portfolio weight of the position.

        Returns
        -------
        float
            New weight, clamped to [-max_position_pct, max_position_pct].
        """
        if current_vol <= 0:
            return 0.0

        new_weight = current_weight * (target_vol / current_vol)
        return float(np.clip(new_weight, -self._max_pct, self._max_pct))

    # ------------------------------------------------------------------
    # Max-drawdown sizing
    # ------------------------------------------------------------------

    def max_drawdown_sizing(
        self,
        current_drawdown: float,
        max_allowed: float,
        current_weight: float,
    ) -> float:
        """Reduce position as drawdown approaches its limit.

        Once the current drawdown exceeds 50 % of *max_allowed*, the
        position is linearly scaled down, reaching zero at *max_allowed*.

        Parameters
        ----------
        current_drawdown:
            Current drawdown as a positive fraction (e.g. 0.08 for 8 %).
        max_allowed:
            Maximum tolerable drawdown (positive fraction).
        current_weight:
            Current portfolio weight of the position.

        Returns
        -------
        float
            Adjusted weight (always >= 0).
        """
        if max_allowed <= 0:
            return 0.0

        factor = max(0.0, 1.0 - (current_drawdown / max_allowed))
        return float(current_weight * factor)
