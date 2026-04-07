"""Portfolio construction and optimization engine.

Provides multiple portfolio optimization methods:
- Mean-variance (Markowitz)
- Minimum variance
- Hierarchical Risk Parity (HRP)
- Black-Litterman
- Risk parity (equal risk contribution)
- Regime-aware allocation
- Efficient frontier computation

All methods accept a polars DataFrame of asset returns with schema:
    - date: Date or Datetime column (optional)
    - One numeric column per asset (asset daily returns)
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import polars as pl
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import minimize
from scipy.spatial.distance import squareform


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class PortfolioResult:
    """Immutable result returned by every optimisation method."""

    weights: dict[str, float]
    expected_return: float
    expected_vol: float
    sharpe_ratio: float
    method: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _asset_columns(returns: pl.DataFrame) -> list[str]:
    """Return non-date numeric column names (one per asset)."""
    return [
        c for c in returns.columns
        if returns[c].dtype in (pl.Float32, pl.Float64, pl.Int64, pl.Int32)
    ]


def _to_numpy(returns: pl.DataFrame) -> tuple[list[str], np.ndarray]:
    """Extract asset names and an (T, N) numpy array from *returns*."""
    cols = _asset_columns(returns)
    if not cols:
        raise ValueError("returns DataFrame has no numeric asset columns")
    mat = returns.select(cols).to_numpy().astype(np.float64)
    return cols, mat


def _cov_and_mu(
    mat: np.ndarray,
    annualise: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (covariance, mean_returns) from a (T, N) matrix.

    When *annualise* is True the outputs are scaled to 252 trading days.
    """
    factor = 252 if annualise else 1
    mu = mat.mean(axis=0) * factor
    cov = np.cov(mat, rowvar=False) * factor
    if cov.ndim == 0:
        cov = np.array([[float(cov)]])
    return cov, mu


def _portfolio_metrics(
    w: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
    risk_free_rate: float = 0.05,
) -> tuple[float, float, float]:
    """Return (expected_return, expected_vol, sharpe_ratio)."""
    ret = float(w @ mu)
    vol = float(np.sqrt(w @ cov @ w))
    sharpe = (ret - risk_free_rate) / vol if vol > 0 else 0.0
    return ret, vol, sharpe


# ---------------------------------------------------------------------------
# Portfolio Optimizer
# ---------------------------------------------------------------------------

class PortfolioOptimizer:
    """Unified portfolio optimisation interface.

    Every public method returns a :class:`PortfolioResult` (except
    :meth:`efficient_frontier` which returns a :class:`pl.DataFrame`).
    """

    # ------------------------------------------------------------------
    # Mean-variance (Markowitz)
    # ------------------------------------------------------------------

    def mean_variance(
        self,
        returns: pl.DataFrame,
        target_return: float | None = None,
        risk_free_rate: float = 0.05,
    ) -> PortfolioResult:
        """Classic Markowitz mean-variance optimisation.

        Parameters
        ----------
        returns:
            DataFrame with one numeric column per asset (daily returns).
        target_return:
            If provided, minimise variance subject to achieving this
            annualised return.  If *None*, maximise the Sharpe ratio
            (tangency portfolio).
        risk_free_rate:
            Annualised risk-free rate used for Sharpe computation.

        Returns
        -------
        PortfolioResult
            Long-only portfolio with weights summing to 1.
        """
        cols, mat = _to_numpy(returns)
        n = len(cols)
        cov, mu = _cov_and_mu(mat)

        bounds = [(0.0, 1.0)] * n
        sum_to_one = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        w0 = np.ones(n) / n

        if target_return is None:
            # Maximise Sharpe  =>  minimise negative Sharpe
            def neg_sharpe(w: np.ndarray) -> float:
                ret = float(w @ mu)
                vol = float(np.sqrt(w @ cov @ w))
                if vol < 1e-12:
                    return 0.0
                return -(ret - risk_free_rate) / vol

            result = minimize(
                neg_sharpe,
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=[sum_to_one],
                options={"maxiter": 1000, "ftol": 1e-12},
            )
        else:
            # Minimise variance s.t. target return
            return_constraint = {
                "type": "eq",
                "fun": lambda w: float(w @ mu) - target_return,
            }

            result = minimize(
                lambda w: float(w @ cov @ w),
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=[sum_to_one, return_constraint],
                options={"maxiter": 1000, "ftol": 1e-12},
            )

        w_opt = result.x
        ret, vol, sharpe = _portfolio_metrics(w_opt, mu, cov, risk_free_rate)

        return PortfolioResult(
            weights=dict(zip(cols, [float(x) for x in w_opt])),
            expected_return=ret,
            expected_vol=vol,
            sharpe_ratio=sharpe,
            method="mean_variance",
        )

    # ------------------------------------------------------------------
    # Minimum variance
    # ------------------------------------------------------------------

    def min_variance(self, returns: pl.DataFrame) -> PortfolioResult:
        """Global minimum-variance portfolio (long-only).

        Parameters
        ----------
        returns:
            DataFrame with one numeric column per asset (daily returns).
        """
        cols, mat = _to_numpy(returns)
        n = len(cols)
        cov, mu = _cov_and_mu(mat)

        bounds = [(0.0, 1.0)] * n
        sum_to_one = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        w0 = np.ones(n) / n

        result = minimize(
            lambda w: float(w @ cov @ w),
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=[sum_to_one],
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        w_opt = result.x
        ret, vol, sharpe = _portfolio_metrics(w_opt, mu, cov)

        return PortfolioResult(
            weights=dict(zip(cols, [float(x) for x in w_opt])),
            expected_return=ret,
            expected_vol=vol,
            sharpe_ratio=sharpe,
            method="min_variance",
        )

    # ------------------------------------------------------------------
    # Hierarchical Risk Parity (Lopez de Prado)
    # ------------------------------------------------------------------

    def hierarchical_risk_parity(
        self,
        returns: pl.DataFrame,
    ) -> PortfolioResult:
        """Hierarchical Risk Parity following Lopez de Prado (2016).

        Steps:
        1. Compute correlation and covariance matrices.
        2. Hierarchical clustering on a correlation-based distance.
        3. Quasi-diagonalise the covariance matrix via the dendrogram.
        4. Recursive bisection to allocate weights.

        Parameters
        ----------
        returns:
            DataFrame with one numeric column per asset (daily returns).
        """
        cols, mat = _to_numpy(returns)
        cov, mu = _cov_and_mu(mat)
        n = len(cols)

        # 1. Correlation distance matrix
        corr = np.corrcoef(mat, rowvar=False)
        dist = np.sqrt(0.5 * (1.0 - corr))
        # Convert to condensed distance vector
        np.fill_diagonal(dist, 0.0)
        condensed = squareform(dist, checks=False)

        # 2. Hierarchical clustering (single linkage)
        link = linkage(condensed, method="single")

        # 3. Quasi-diagonalisation: order assets by dendrogram leaves
        sort_ix = self._get_quasi_diag(link, n)

        # 4. Recursive bisection
        w = np.zeros(n)
        cluster_weights = self._recursive_bisection(cov, sort_ix)
        for idx, weight in zip(sort_ix, cluster_weights):
            w[idx] = weight

        # Normalise (should already sum to ~1, but guard against fp drift)
        w = w / w.sum()

        ret, vol, sharpe = _portfolio_metrics(w, mu, cov)

        return PortfolioResult(
            weights=dict(zip(cols, [float(x) for x in w])),
            expected_return=ret,
            expected_vol=vol,
            sharpe_ratio=sharpe,
            method="hierarchical_risk_parity",
        )

    @staticmethod
    def _get_quasi_diag(link: np.ndarray, n: int) -> list[int]:
        """Return leaf ordering from a linkage matrix (dendrogram)."""
        sort_ix: list[int] = list(range(n))
        # Walk the linkage bottom-up
        # Each row of link: [left, right, dist, count]
        # Cluster IDs >= n are merged clusters
        node_order: dict[int, list[int]] = {i: [i] for i in range(n)}
        for i, row in enumerate(link):
            left_id = int(row[0])
            right_id = int(row[1])
            new_id = n + i
            node_order[new_id] = node_order[left_id] + node_order[right_id]
        # The last merged cluster spans all leaves
        root = n + len(link) - 1
        return node_order[root]

    @staticmethod
    def _recursive_bisection(
        cov: np.ndarray,
        sort_ix: list[int],
    ) -> list[float]:
        """Allocate weights by recursive bisection on sorted indices."""
        n = len(sort_ix)
        weights = np.ones(n)

        items: list[list[int]] = [list(range(n))]  # positions in sort_ix

        while items:
            next_items: list[list[int]] = []
            for subset in items:
                if len(subset) <= 1:
                    continue
                mid = len(subset) // 2
                left = subset[:mid]
                right = subset[mid:]

                # Cluster variance for left and right
                left_assets = [sort_ix[i] for i in left]
                right_assets = [sort_ix[i] for i in right]

                var_left = _cluster_variance(cov, left_assets)
                var_right = _cluster_variance(cov, right_assets)

                # Allocate inversely proportional to variance
                total = var_left + var_right
                if total < 1e-16:
                    alpha = 0.5
                else:
                    alpha = 1.0 - var_left / total

                for i in left:
                    weights[i] *= alpha
                for i in right:
                    weights[i] *= (1.0 - alpha)

                next_items.append(left)
                next_items.append(right)

            items = next_items

        return weights.tolist()

    # ------------------------------------------------------------------
    # Black-Litterman
    # ------------------------------------------------------------------

    def black_litterman(
        self,
        returns: pl.DataFrame,
        market_caps: dict[str, float],
        views: list[dict],
        tau: float = 0.05,
        risk_free_rate: float = 0.05,
    ) -> PortfolioResult:
        """Black-Litterman model combining equilibrium returns with views.

        Parameters
        ----------
        returns:
            DataFrame with one numeric column per asset (daily returns).
        market_caps:
            Market capitalisations keyed by asset name.  Used for
            reverse-optimisation of equilibrium returns.
        views:
            List of investor view dicts, each containing:
            - ``assets``: list of asset names (length 1 for absolute views,
              length 2 for relative views where the view is
              ``assets[0] - assets[1]``).
            - ``returns``: expected annualised return for the view.
            - ``confidence``: float in (0, 1]; higher = more confident.
        tau:
            Uncertainty parameter for the prior (typically 0.01 - 0.10).
        risk_free_rate:
            Annualised risk-free rate.
        """
        cols, mat = _to_numpy(returns)
        n = len(cols)
        cov, _ = _cov_and_mu(mat)
        col_to_idx = {c: i for i, c in enumerate(cols)}

        # Market-cap weights (equilibrium weights)
        cap_arr = np.array([market_caps.get(c, 1.0) for c in cols], dtype=np.float64)
        w_mkt = cap_arr / cap_arr.sum()

        # Implied risk-aversion coefficient (delta)
        port_var = float(w_mkt @ cov @ w_mkt)
        if port_var < 1e-16:
            delta = 2.5  # fallback
        else:
            delta = (float(w_mkt @ (cov @ w_mkt)) - risk_free_rate) / port_var
            if delta <= 0:
                delta = 2.5

        # Equilibrium excess returns: pi = delta * Sigma * w_mkt
        pi = delta * cov @ w_mkt

        # Build P (pick matrix) and Q (view returns) and Omega (confidence)
        k = len(views)
        if k == 0:
            # No views -- just use equilibrium
            posterior_mu = pi
        else:
            P = np.zeros((k, n))
            Q = np.zeros(k)
            omega_diag = np.zeros(k)

            for vi, view in enumerate(views):
                assets = view["assets"]
                Q[vi] = view["returns"]
                confidence = view.get("confidence", 0.5)

                if len(assets) == 1:
                    # Absolute view
                    idx = col_to_idx[assets[0]]
                    P[vi, idx] = 1.0
                elif len(assets) == 2:
                    # Relative view: assets[0] outperforms assets[1]
                    P[vi, col_to_idx[assets[0]]] = 1.0
                    P[vi, col_to_idx[assets[1]]] = -1.0
                else:
                    raise ValueError(
                        f"View must have 1 or 2 assets, got {len(assets)}"
                    )

                # Omega diagonal: lower confidence => higher uncertainty
                omega_diag[vi] = (1.0 / confidence - 1.0) * float(P[vi] @ (tau * cov) @ P[vi])

            Omega = np.diag(omega_diag)

            # Posterior mean: mu_BL = [(tau*Sigma)^-1 + P'*Omega^-1*P]^-1
            #                         * [(tau*Sigma)^-1*pi + P'*Omega^-1*Q]
            tau_cov_inv = np.linalg.inv(tau * cov)
            Omega_inv = np.linalg.inv(Omega)

            M = np.linalg.inv(tau_cov_inv + P.T @ Omega_inv @ P)
            posterior_mu = M @ (tau_cov_inv @ pi + P.T @ Omega_inv @ Q)

        # Optimise with posterior returns
        bounds = [(0.0, 1.0)] * n
        sum_to_one = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        w0 = np.ones(n) / n

        def neg_sharpe(w: np.ndarray) -> float:
            ret = float(w @ posterior_mu)
            vol = float(np.sqrt(w @ cov @ w))
            if vol < 1e-12:
                return 0.0
            return -(ret - risk_free_rate) / vol

        result = minimize(
            neg_sharpe,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=[sum_to_one],
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        w_opt = result.x
        ret, vol, sharpe = _portfolio_metrics(w_opt, posterior_mu, cov, risk_free_rate)

        return PortfolioResult(
            weights=dict(zip(cols, [float(x) for x in w_opt])),
            expected_return=ret,
            expected_vol=vol,
            sharpe_ratio=sharpe,
            method="black_litterman",
        )

    # ------------------------------------------------------------------
    # Risk parity (equal risk contribution)
    # ------------------------------------------------------------------

    def risk_parity(
        self,
        returns: pl.DataFrame,
        target_vol: float = 0.10,
    ) -> PortfolioResult:
        """Equal risk contribution portfolio.

        Each asset contributes equally to total portfolio volatility.
        The approach mirrors ``risk.position_sizing.engine`` but wraps
        the result in a :class:`PortfolioResult`.

        Parameters
        ----------
        returns:
            DataFrame with one numeric column per asset (daily returns).
        target_vol:
            Desired annualised portfolio volatility for rescaling.
        """
        cols, mat = _to_numpy(returns)
        n = len(cols)
        cov, mu = _cov_and_mu(mat)

        # Risk-parity via scipy optimisation: minimise the sum of
        # squared differences between each asset's risk contribution
        # and the target (1/N).

        def _risk_parity_obj(w: np.ndarray) -> float:
            port_vol = np.sqrt(w @ cov @ w)
            if port_vol < 1e-16:
                return 1e6
            marginal = cov @ w
            rc = w * marginal / port_vol
            rc_pct = rc / rc.sum()
            target_rc = np.ones(n) / n
            return float(np.sum((rc_pct - target_rc) ** 2))

        bounds = [(1e-6, 1.0)] * n
        sum_to_one = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        w0 = np.ones(n) / n

        result_opt = minimize(
            _risk_parity_obj,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=[sum_to_one],
            options={"maxiter": 2000, "ftol": 1e-14},
        )
        w_norm = result_opt.x
        w_norm = w_norm / w_norm.sum()

        ret, vol, sharpe = _portfolio_metrics(w_norm, mu, cov)

        return PortfolioResult(
            weights=dict(zip(cols, [float(x) for x in w_norm])),
            expected_return=ret,
            expected_vol=vol,
            sharpe_ratio=sharpe,
            method="risk_parity",
        )

    # ------------------------------------------------------------------
    # Regime-aware allocation
    # ------------------------------------------------------------------

    def regime_aware(
        self,
        returns: pl.DataFrame,
        n_regimes: int = 2,
        vol_window: int = 21,
    ) -> PortfolioResult:
        """Regime-aware portfolio allocation.

        Uses a rolling-volatility threshold to classify market regimes
        (e.g. low-vol / high-vol).  In high-vol regimes the allocation
        shifts toward the minimum-variance portfolio; in low-vol regimes
        the mean-variance tangency portfolio is used.

        Parameters
        ----------
        returns:
            DataFrame with one numeric column per asset (daily returns).
        n_regimes:
            Number of volatility regimes (currently supports 2).
        vol_window:
            Rolling window (in trading days) for regime detection.
        """
        cols, mat = _to_numpy(returns)
        n = len(cols)
        cov, mu = _cov_and_mu(mat)

        # Equal-weight portfolio returns for regime detection
        eq_returns = mat.mean(axis=1)

        # Rolling volatility of equal-weight portfolio
        if len(eq_returns) < vol_window:
            vol_window = max(2, len(eq_returns))
        rolling_vol = np.array([
            np.std(eq_returns[max(0, i - vol_window + 1):i + 1], ddof=1)
            for i in range(len(eq_returns))
        ])

        # Classify most recent observation into regime
        if n_regimes == 2:
            median_vol = np.median(rolling_vol[vol_window - 1:])
            current_vol = rolling_vol[-1]
            high_vol_regime = current_vol > median_vol
        else:
            # For n_regimes > 2 use quantile thresholds
            valid_vols = rolling_vol[vol_window - 1:]
            thresholds = np.linspace(0, 100, n_regimes + 1)[1:-1]
            percentiles = np.percentile(valid_vols, thresholds)
            regime = int(np.searchsorted(percentiles, rolling_vol[-1]))
            high_vol_regime = regime >= (n_regimes - 1)

        if high_vol_regime:
            # Defensive: minimum-variance portfolio
            result = self.min_variance(returns)
            result.method = "regime_aware"
            return result
        else:
            # Aggressive: tangency (max-Sharpe) portfolio
            result = self.mean_variance(returns)
            result.method = "regime_aware"
            return result

    # ------------------------------------------------------------------
    # Efficient frontier
    # ------------------------------------------------------------------

    def efficient_frontier(
        self,
        returns: pl.DataFrame,
        n_points: int = 50,
        risk_free_rate: float = 0.05,
    ) -> pl.DataFrame:
        """Compute portfolios along the efficient frontier.

        Parameters
        ----------
        returns:
            DataFrame with one numeric column per asset (daily returns).
        n_points:
            Number of frontier portfolios to compute.
        risk_free_rate:
            Annualised risk-free rate for Sharpe computation.

        Returns
        -------
        pl.DataFrame
            Columns: target_return, expected_return, expected_vol,
            sharpe_ratio, weights_json.
        """
        cols, mat = _to_numpy(returns)
        cov, mu = _cov_and_mu(mat)

        # Determine feasible return range (long-only)
        min_ret = float(mu.min())
        max_ret = float(mu.max())
        target_returns = np.linspace(min_ret, max_ret, n_points)

        rows: list[dict] = []
        for target in target_returns:
            try:
                result = self.mean_variance(
                    returns,
                    target_return=target,
                    risk_free_rate=risk_free_rate,
                )
                rows.append(
                    {
                        "target_return": target,
                        "expected_return": result.expected_return,
                        "expected_vol": result.expected_vol,
                        "sharpe_ratio": result.sharpe_ratio,
                        "weights_json": json.dumps(result.weights),
                    }
                )
            except Exception:
                # Some target returns may be infeasible under long-only
                continue

        return pl.DataFrame(rows)


# ---------------------------------------------------------------------------
# Module-level helpers used by HRP
# ---------------------------------------------------------------------------

def _cluster_variance(cov: np.ndarray, indices: list[int]) -> float:
    """Inverse-variance-weighted cluster variance for HRP bisection."""
    sub_cov = cov[np.ix_(indices, indices)]
    # Inverse-variance portfolio within the cluster
    ivp = 1.0 / np.diag(sub_cov)
    ivp = ivp / ivp.sum()
    return float(ivp @ sub_cov @ ivp)
