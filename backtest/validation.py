"""Backtest validation tools to combat overfitting.

Implements deflated Sharpe ratio, multiple testing corrections (Bonferroni,
Benjamini-Hochberg), Monte Carlo permutation tests, and combinatorial purged
cross-validation (CPCV) following Lopez de Prado's methodology.

Reference: Lopez de Prado, *Advances in Financial Machine Learning*, Ch. 11-12.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import polars as pl
from scipy import stats as scipy_stats

if TYPE_CHECKING:
    from core.backtest import BacktestResult


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

EULER_MASCHERONI = 0.5772156649015329


@dataclass
class ValidationResult:
    """Result of backtest validation against overfitting."""

    is_valid: bool
    deflated_sharpe: float
    original_sharpe: float
    p_value: float
    n_trials: int
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class BacktestValidator:
    """Validate backtest results against overfitting.

    Implements deflated Sharpe ratio, multiple testing corrections,
    and Monte Carlo permutation tests.
    """

    # ------------------------------------------------------------------
    # Deflated Sharpe Ratio
    # ------------------------------------------------------------------

    @staticmethod
    def deflated_sharpe_ratio(
        sharpe: float,
        n_trials: int,
        n_observations: int,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
    ) -> ValidationResult:
        """Compute the deflated Sharpe ratio (Lopez de Prado).

        Adjusts the observed Sharpe ratio for multiple testing by comparing
        it against E[max(Sharpe)] under the null hypothesis of zero true
        Sharpe across *n_trials* independent trials.

        Args:
            sharpe: Observed (annualised) Sharpe ratio.
            n_trials: Number of strategy trials / parameter combos tested.
            n_observations: Number of return observations used.
            skewness: Skewness of the return series (default 0).
            kurtosis: Kurtosis of the return series (default 3, i.e. normal).

        Returns:
            ValidationResult with deflated Sharpe, p-value, and validity flag.
        """
        warnings: list[str] = []

        if n_trials < 1:
            n_trials = 1
            warnings.append("n_trials clamped to 1.")

        if n_observations < 2:
            return ValidationResult(
                is_valid=False,
                deflated_sharpe=0.0,
                original_sharpe=sharpe,
                p_value=1.0,
                n_trials=n_trials,
                warnings=["Insufficient observations."],
            )

        # Expected maximum Sharpe under the null (Euler-Mascheroni approx.)
        if n_trials == 1:
            e_max_sharpe = 0.0
        else:
            ln_n = math.log(n_trials)
            sqrt_2ln = math.sqrt(2.0 * ln_n)
            e_max_sharpe = (
                sqrt_2ln
                * (1.0 - EULER_MASCHERONI / ln_n)
                + EULER_MASCHERONI / sqrt_2ln
            )

        # Standard error of the Sharpe ratio accounting for higher moments
        sr_std = math.sqrt(
            (1.0 - skewness * sharpe + ((kurtosis - 1.0) / 4.0) * sharpe**2)
            / (n_observations - 1.0)
        )

        if sr_std < 1e-12:
            sr_std = 1e-12

        # Deflated Sharpe = (SR_obs - E[max SR]) / std(SR)
        dsr = (sharpe - e_max_sharpe) / sr_std

        # One-sided p-value (is the observed SR significantly above expected max?)
        p_value = float(1.0 - scipy_stats.norm.cdf(dsr))

        is_valid = p_value < 0.05

        if n_trials > 20:
            warnings.append(
                f"High trial count ({n_trials}): results may be heavily penalised."
            )

        return ValidationResult(
            is_valid=is_valid,
            deflated_sharpe=float(dsr),
            original_sharpe=sharpe,
            p_value=p_value,
            n_trials=n_trials,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Multiple testing corrections
    # ------------------------------------------------------------------

    @staticmethod
    def bonferroni_correction(
        p_values: list[float],
        alpha: float = 0.05,
    ) -> pl.DataFrame:
        """Apply Bonferroni correction for family-wise error rate control.

        Args:
            p_values: Raw p-values from independent tests.
            alpha: Significance threshold (default 0.05).

        Returns:
            DataFrame with columns [test_index, original_p, adjusted_p, is_significant].
        """
        n_tests = len(p_values)
        adjusted = [min(p * n_tests, 1.0) for p in p_values]

        return pl.DataFrame(
            {
                "test_index": list(range(n_tests)),
                "original_p": p_values,
                "adjusted_p": adjusted,
                "is_significant": [a < alpha for a in adjusted],
            }
        )

    @staticmethod
    def benjamini_hochberg(
        p_values: list[float],
        alpha: float = 0.05,
    ) -> pl.DataFrame:
        """Apply Benjamini-Hochberg procedure for false discovery rate control.

        Args:
            p_values: Raw p-values from independent tests.
            alpha: Target FDR level (default 0.05).

        Returns:
            DataFrame with columns [test_index, original_p, adjusted_p, is_significant].
        """
        m = len(p_values)
        indexed = sorted(enumerate(p_values), key=lambda x: x[1])

        # Compute adjusted p-values (step-up)
        adjusted = [0.0] * m
        prev = 1.0
        for rank_idx in range(m - 1, -1, -1):
            orig_idx, p = indexed[rank_idx]
            k = rank_idx + 1  # 1-based rank
            adj = min(p * m / k, prev)
            adj = min(adj, 1.0)
            adjusted[orig_idx] = adj
            prev = adj

        # Significance: find the largest k where p_(k) <= k/m * alpha
        is_significant = [False] * m
        max_k = 0
        for rank_idx, (orig_idx, p) in enumerate(indexed):
            k = rank_idx + 1
            threshold = k / m * alpha
            if p <= threshold:
                max_k = k

        # All tests with rank <= max_k are significant
        for rank_idx in range(max_k):
            orig_idx, _ = indexed[rank_idx]
            is_significant[orig_idx] = True

        return pl.DataFrame(
            {
                "test_index": list(range(m)),
                "original_p": p_values,
                "adjusted_p": adjusted,
                "is_significant": is_significant,
            }
        )

    # ------------------------------------------------------------------
    # Monte Carlo permutation test
    # ------------------------------------------------------------------

    @staticmethod
    def monte_carlo_permutation_test(
        returns: pl.DataFrame,
        n_permutations: int = 1000,
        seed: int | None = None,
    ) -> dict[str, float]:
        """Permutation test for the significance of a backtest Sharpe ratio.

        Shuffles the return series *n_permutations* times, computes the Sharpe
        ratio for each permutation, and compares the original against the
        null distribution.

        Args:
            returns: DataFrame with a ``returns`` column (daily returns).
            n_permutations: Number of random permutations.
            seed: Optional RNG seed for reproducibility.

        Returns:
            Dict with original_sharpe, permuted_mean, permuted_std, p_value,
            and percentile.
        """
        ret_array = returns.get_column("returns").to_numpy()

        def _sharpe(r: np.ndarray) -> float:
            if r.std() < 1e-12:
                return 0.0
            return float(r.mean() / r.std() * np.sqrt(252))

        original_sharpe = _sharpe(ret_array)

        rng = np.random.default_rng(seed)
        permuted_sharpes = np.empty(n_permutations)
        for i in range(n_permutations):
            shuffled = rng.permutation(ret_array)
            permuted_sharpes[i] = _sharpe(shuffled)

        permuted_mean = float(permuted_sharpes.mean())
        permuted_std = float(permuted_sharpes.std())
        p_value = float(np.mean(permuted_sharpes >= original_sharpe))
        percentile = float(
            scipy_stats.percentileofscore(permuted_sharpes, original_sharpe)
        )

        return {
            "original_sharpe": original_sharpe,
            "permuted_mean": permuted_mean,
            "permuted_std": permuted_std,
            "p_value": p_value,
            "percentile": percentile,
        }

    # ------------------------------------------------------------------
    # Combinatorial Purged Cross-Validation (CPCV)
    # ------------------------------------------------------------------

    @staticmethod
    def combinatorial_purged_cv(
        X: np.ndarray,
        y: np.ndarray,
        model: Any,
        n_splits: int = 5,
        n_test_groups: int = 2,
        purge_window: int = 5,
    ) -> dict[str, Any]:
        """Combinatorial purged cross-validation (Lopez de Prado).

        Evaluates all C(n_splits, n_test_groups) train/test combinations.
        Purging removes *purge_window* observations adjacent to the
        train/test boundary to prevent information leakage.

        Args:
            X: Feature array of shape (n_samples, n_features).
            y: Target array of shape (n_samples,).
            model: Sklearn-compatible estimator with fit/predict.
            n_splits: Number of contiguous groups to partition data into.
            n_test_groups: Number of groups held out for testing per combo.
            purge_window: Number of observations to purge at boundaries.

        Returns:
            Dict with mean_score, std_score, n_combinations, fold_scores,
            and probability_of_backtest_overfitting.
        """
        n_samples = len(y)
        group_size = n_samples // n_splits
        group_indices = []
        for g in range(n_splits):
            start = g * group_size
            end = start + group_size if g < n_splits - 1 else n_samples
            group_indices.append(np.arange(start, end))

        combos = list(itertools.combinations(range(n_splits), n_test_groups))
        fold_scores: list[float] = []

        for test_groups in combos:
            test_groups_set = set(test_groups)
            train_groups = [g for g in range(n_splits) if g not in test_groups_set]

            test_idx = np.concatenate([group_indices[g] for g in test_groups])
            train_idx = np.concatenate([group_indices[g] for g in train_groups])

            # Purge: remove train observations near test boundaries
            if purge_window > 0:
                test_min, test_max = int(test_idx.min()), int(test_idx.max())
                purge_mask = (
                    (train_idx >= test_min - purge_window)
                    & (train_idx <= test_max + purge_window)
                )
                # Only remove observations that are in the purge zone AND
                # adjacent to test boundaries (not deep inside train blocks)
                boundary_zones = set()
                for g in test_groups:
                    g_start = int(group_indices[g][0])
                    g_end = int(group_indices[g][-1])
                    for idx in range(g_start - purge_window, g_start):
                        boundary_zones.add(idx)
                    for idx in range(g_end + 1, g_end + 1 + purge_window):
                        boundary_zones.add(idx)

                train_idx = np.array(
                    [i for i in train_idx if i not in boundary_zones]
                )

            if len(train_idx) == 0 or len(test_idx) == 0:
                continue

            X_train, y_train = X[train_idx], y[train_idx]
            X_test, y_test = X[test_idx], y[test_idx]

            model.fit(X_train, y_train)
            preds = model.predict(X_test)

            # Use accuracy for classification-like targets
            score = float(np.mean(preds == y_test)) if _is_classification(y_test) else float(
                1.0 - np.mean((preds - y_test) ** 2) / (np.var(y_test) + 1e-12)
            )
            fold_scores.append(score)

        mean_score = float(np.mean(fold_scores)) if fold_scores else 0.0
        std_score = float(np.std(fold_scores)) if fold_scores else 0.0

        # Probability of backtest overfitting = fraction of combos with
        # negative OOS performance (score below baseline)
        baseline = 0.5 if _is_classification(y) else 0.0
        n_negative = sum(1 for s in fold_scores if s < baseline)
        pbo = n_negative / len(fold_scores) if fold_scores else 1.0

        return {
            "mean_score": mean_score,
            "std_score": std_score,
            "n_combinations": len(combos),
            "fold_scores": fold_scores,
            "probability_of_backtest_overfitting": pbo,
        }

    # ------------------------------------------------------------------
    # Convenience entry point
    # ------------------------------------------------------------------

    @classmethod
    def validate_backtest(
        cls,
        backtest_result: BacktestResult,
        n_trials: int = 1,
        returns: pl.DataFrame | None = None,
    ) -> ValidationResult:
        """Validate a backtest result against overfitting.

        Runs the deflated Sharpe ratio test and, if return data is provided,
        a Monte Carlo permutation test.

        Args:
            backtest_result: A BacktestResult from any backtest engine.
            n_trials: Number of strategy variants tested.
            returns: Optional DataFrame with a ``returns`` column for the
                     permutation test.

        Returns:
            A combined ValidationResult.
        """
        warnings: list[str] = []

        # Derive observation count from equity curve
        n_obs = backtest_result.equity_curve.height

        dsr_result = cls.deflated_sharpe_ratio(
            sharpe=backtest_result.sharpe_ratio,
            n_trials=n_trials,
            n_observations=n_obs,
        )
        warnings.extend(dsr_result.warnings)

        # Run permutation test if returns provided
        if returns is not None and returns.height > 10:
            perm = cls.monte_carlo_permutation_test(returns, n_permutations=500, seed=42)
            if perm["p_value"] > 0.05:
                warnings.append(
                    f"Permutation test not significant (p={perm['p_value']:.3f})."
                )
            # Override validity: both tests must pass
            perm_valid = perm["p_value"] < 0.05
            is_valid = dsr_result.is_valid and perm_valid
        else:
            is_valid = dsr_result.is_valid
            if returns is None:
                warnings.append("No returns provided; skipping permutation test.")

        return ValidationResult(
            is_valid=is_valid,
            deflated_sharpe=dsr_result.deflated_sharpe,
            original_sharpe=dsr_result.original_sharpe,
            p_value=dsr_result.p_value,
            n_trials=n_trials,
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_classification(y: np.ndarray) -> bool:
    """Heuristic: treat as classification if target has few unique values."""
    unique = np.unique(y)
    return len(unique) <= 20 and np.all(unique == unique.astype(int))
