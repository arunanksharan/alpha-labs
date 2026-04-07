"""Purged K-Fold cross-validation for financial machine learning.

Standard K-fold CV leaks information through temporal autocorrelation in
financial time series.  This module implements purging and embargo to
eliminate look-ahead bias.

Reference: López de Prado, *Advances in Financial Machine Learning*, Ch. 7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl
from sklearn.metrics import accuracy_score, roc_auc_score


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CVFold:
    """A single cross-validation fold with index arrays and boundary info."""

    train_indices: np.ndarray
    test_indices: np.ndarray
    train_start: int
    train_end: int
    test_start: int
    test_end: int


# ---------------------------------------------------------------------------
# Purged K-Fold
# ---------------------------------------------------------------------------

class PurgedKFoldCV:
    """K-fold cross-validation with purging and embargo for time series.

    Purging: removes training observations whose labels overlap with test period.
    Embargo: adds a gap between train and test to prevent information leakage.

    Parameters
    ----------
    n_splits : int
        Number of contiguous time-ordered folds.
    purge_window : int
        Number of samples to remove from training data on each side of the
        test boundary.
    embargo_pct : float
        Fraction of total samples to embargo immediately after the test
        set end.  Training observations in this zone are dropped.
    """

    def __init__(
        self,
        n_splits: int = 5,
        purge_window: int = 5,
        embargo_pct: float = 0.01,
    ) -> None:
        if n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        self.n_splits = n_splits
        self.purge_window = purge_window
        self.embargo_pct = embargo_pct

    # ------------------------------------------------------------------
    # split
    # ------------------------------------------------------------------

    def split(
        self,
        X: pl.DataFrame | np.ndarray,
        dates: pl.Series | np.ndarray | None = None,
    ) -> list[CVFold]:
        """Generate purged K-fold splits.

        Parameters
        ----------
        X : pl.DataFrame | np.ndarray
            Feature matrix.  Only its length matters for splitting.
        dates : pl.Series | np.ndarray | None
            Optional date / timestamp column.  When provided the data is
            sorted by date before splitting (the returned indices refer to
            the *sorted* order).

        Returns
        -------
        list[CVFold]
            One ``CVFold`` per fold.
        """
        n_samples = len(X)
        if n_samples < self.n_splits:
            raise ValueError(
                f"Cannot create {self.n_splits} folds from {n_samples} samples"
            )

        # If dates provided, obtain sorted order
        if dates is not None:
            if isinstance(dates, pl.Series):
                sorted_idx = np.argsort(dates.to_numpy())
            else:
                sorted_idx = np.argsort(dates)
        else:
            sorted_idx = np.arange(n_samples)

        embargo_size = max(1, int(n_samples * self.embargo_pct))

        # Create contiguous blocks of roughly equal size
        fold_boundaries = np.array_split(np.arange(n_samples), self.n_splits)

        folds: list[CVFold] = []
        for k in range(self.n_splits):
            test_positions = fold_boundaries[k]
            test_start = int(test_positions[0])
            test_end = int(test_positions[-1])

            # Build train positions = everything not in test
            train_positions = np.concatenate(
                [fold_boundaries[j] for j in range(self.n_splits) if j != k]
            )

            # --- Purge: remove training samples within purge_window of test ---
            purge_start = max(0, test_start - self.purge_window)
            purge_end = min(n_samples - 1, test_end + self.purge_window)
            purge_zone = set(range(purge_start, purge_end + 1))

            # --- Embargo: remove train samples right after test end ---
            embargo_start = test_end + 1
            embargo_end = min(n_samples - 1, test_end + embargo_size)
            embargo_zone = set(range(embargo_start, embargo_end + 1))

            excluded = purge_zone | embargo_zone
            train_positions = np.array(
                [p for p in train_positions if p not in excluded]
            )

            # Map positions back to original indices through sorted_idx
            train_indices = sorted_idx[train_positions]
            test_indices = sorted_idx[test_positions]

            folds.append(
                CVFold(
                    train_indices=train_indices,
                    test_indices=test_indices,
                    train_start=int(train_positions[0]) if len(train_positions) > 0 else 0,
                    train_end=int(train_positions[-1]) if len(train_positions) > 0 else 0,
                    test_start=test_start,
                    test_end=test_end,
                )
            )

        return folds

    # ------------------------------------------------------------------
    # score
    # ------------------------------------------------------------------

    def score(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        dates: np.ndarray | None = None,
        metric: str = "accuracy",
    ) -> dict[str, Any]:
        """Run full CV loop and return per-fold and aggregate scores.

        Parameters
        ----------
        model
            Scikit-learn compatible estimator (must implement ``fit`` and
            ``predict``; ``predict_proba`` required for ``"auc"``).
        X : np.ndarray
            Feature matrix, shape ``(n_samples, n_features)``.
        y : np.ndarray
            Target array, shape ``(n_samples,)``.
        dates : np.ndarray | None
            Optional date array for date-aware splitting.
        metric : str
            One of ``"accuracy"``, ``"auc"``, ``"sharpe"``.

        Returns
        -------
        dict
            ``{"fold_scores": [...], "mean_score": float, "std_score": float}``
        """
        valid_metrics = {"accuracy", "auc", "sharpe"}
        if metric not in valid_metrics:
            raise ValueError(f"metric must be one of {valid_metrics}, got '{metric}'")

        folds = self.split(
            np.zeros(len(X)),  # placeholder — only length matters
            dates=dates,
        )

        fold_scores: list[float] = []
        for fold in folds:
            X_train, y_train = X[fold.train_indices], y[fold.train_indices]
            X_test, y_test = X[fold.test_indices], y[fold.test_indices]

            from sklearn.base import clone

            cloned = clone(model)
            cloned.fit(X_train, y_train)

            if metric == "accuracy":
                preds = cloned.predict(X_test)
                fold_scores.append(float(accuracy_score(y_test, preds)))

            elif metric == "auc":
                probas = cloned.predict_proba(X_test)[:, 1]
                fold_scores.append(float(roc_auc_score(y_test, probas)))

            elif metric == "sharpe":
                preds = cloned.predict(X_test)
                # Treat predictions as position signals (+1 / -1) and
                # y as actual returns to compute a pseudo-Sharpe ratio.
                returns = preds * y_test
                mean_r = float(np.mean(returns))
                std_r = float(np.std(returns, ddof=1))
                sharpe = mean_r / std_r * np.sqrt(252) if std_r > 0 else 0.0
                fold_scores.append(float(sharpe))

        scores_arr = np.array(fold_scores)
        return {
            "fold_scores": fold_scores,
            "mean_score": float(np.mean(scores_arr)),
            "std_score": float(np.std(scores_arr, ddof=1)),
        }
