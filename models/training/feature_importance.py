"""Feature importance methods for financial machine learning.

Implements MDI, MDA, SFI, and clustered importance following the
methodology in López de Prado, *Advances in Financial Machine Learning*.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import polars as pl
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.metrics import accuracy_score

from models.training.cross_validation import PurgedKFoldCV


class FeatureImportance:
    """Feature importance using MDI, MDA, SFI, and clustered methods.

    Parameters
    ----------
    cv : PurgedKFoldCV | None
        Cross-validator used by ``sfi`` and ``mda``.  When *None* a
        default ``PurgedKFoldCV(n_splits=5)`` is created on demand.
    """

    def __init__(self, cv: PurgedKFoldCV | None = None) -> None:
        self.cv = cv

    def _get_cv(self) -> PurgedKFoldCV:
        if self.cv is None:
            return PurgedKFoldCV(n_splits=5)
        return self.cv

    # ------------------------------------------------------------------
    # MDI — Mean Decrease Impurity
    # ------------------------------------------------------------------

    def mdi(
        self,
        model: Any,
        feature_names: list[str],
    ) -> pl.DataFrame:
        """Mean Decrease Impurity (built-in tree feature importances).

        Parameters
        ----------
        model
            A *fitted* tree-based estimator exposing ``feature_importances_``.
        feature_names : list[str]
            Human-readable feature names matching the training columns.

        Returns
        -------
        pl.DataFrame
            Columns: ``[feature, importance, rank]``, sorted by importance
            descending.
        """
        importances = np.array(model.feature_importances_, dtype=np.float64)
        if len(importances) != len(feature_names):
            raise ValueError(
                f"model has {len(importances)} features but "
                f"{len(feature_names)} names were provided"
            )

        order = np.argsort(-importances)
        ranks = np.empty_like(order)
        ranks[order] = np.arange(1, len(order) + 1)

        return pl.DataFrame(
            {
                "feature": feature_names,
                "importance": importances.tolist(),
                "rank": ranks.tolist(),
            }
        ).sort("importance", descending=True)

    # ------------------------------------------------------------------
    # MDA — Mean Decrease Accuracy (permutation importance)
    # ------------------------------------------------------------------

    def mda(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str],
        n_repeats: int = 10,
    ) -> pl.DataFrame:
        """Mean Decrease Accuracy via permutation importance.

        For each feature the column is randomly shuffled ``n_repeats``
        times and the drop in accuracy is recorded.

        Parameters
        ----------
        model
            A *fitted* estimator with a ``predict`` method.
        X : np.ndarray
            Feature matrix, shape ``(n_samples, n_features)``.
        y : np.ndarray
            Target array.
        feature_names : list[str]
            Feature names.
        n_repeats : int
            Number of random permutations per feature.

        Returns
        -------
        pl.DataFrame
            Columns: ``[feature, importance, importance_std, rank]``.
        """
        rng = np.random.default_rng(42)
        baseline = float(accuracy_score(y, model.predict(X)))

        imp_means: list[float] = []
        imp_stds: list[float] = []

        for col_idx in range(X.shape[1]):
            scores: list[float] = []
            for _ in range(n_repeats):
                X_perm = X.copy()
                rng.shuffle(X_perm[:, col_idx])
                perm_score = float(accuracy_score(y, model.predict(X_perm)))
                scores.append(baseline - perm_score)
            imp_means.append(float(np.mean(scores)))
            imp_stds.append(float(np.std(scores, ddof=1)))

        imp_arr = np.array(imp_means)
        order = np.argsort(-imp_arr)
        ranks = np.empty_like(order)
        ranks[order] = np.arange(1, len(order) + 1)

        return pl.DataFrame(
            {
                "feature": feature_names,
                "importance": imp_means,
                "importance_std": imp_stds,
                "rank": ranks.tolist(),
            }
        ).sort("importance", descending=True)

    # ------------------------------------------------------------------
    # SFI — Single Feature Importance
    # ------------------------------------------------------------------

    def sfi(
        self,
        model_factory: Callable[[], Any],
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str],
    ) -> pl.DataFrame:
        """Single Feature Importance.

        Trains a separate model on each individual feature and scores it
        using purged K-fold CV.

        Parameters
        ----------
        model_factory
            Callable returning a fresh (unfitted) estimator.
        X : np.ndarray
            Feature matrix, shape ``(n_samples, n_features)``.
        y : np.ndarray
            Target array.
        feature_names : list[str]
            Feature names.

        Returns
        -------
        pl.DataFrame
            Columns: ``[feature, importance, rank]``.
        """
        cv = self._get_cv()
        scores: list[float] = []

        for col_idx in range(X.shape[1]):
            X_single = X[:, col_idx : col_idx + 1]
            result = cv.score(model_factory(), X_single, y, metric="accuracy")
            scores.append(result["mean_score"])

        imp_arr = np.array(scores)
        order = np.argsort(-imp_arr)
        ranks = np.empty_like(order)
        ranks[order] = np.arange(1, len(order) + 1)

        return pl.DataFrame(
            {
                "feature": feature_names,
                "importance": scores,
                "rank": ranks.tolist(),
            }
        ).sort("importance", descending=True)

    # ------------------------------------------------------------------
    # Clustered importance
    # ------------------------------------------------------------------

    def clustered_importance(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str],
        n_clusters: int = 5,
    ) -> pl.DataFrame:
        """Clustered MDA importance.

        Groups correlated features using hierarchical clustering on the
        correlation matrix, then measures permutation importance at the
        cluster level (shuffling all features in a cluster simultaneously).

        Parameters
        ----------
        model
            A *fitted* estimator with a ``predict`` method.
        X : np.ndarray
            Feature matrix, shape ``(n_samples, n_features)``.
        y : np.ndarray
            Target array.
        feature_names : list[str]
            Feature names.
        n_clusters : int
            Number of clusters to form.

        Returns
        -------
        pl.DataFrame
            Columns: ``[cluster, features, importance]``.
        """
        n_features = X.shape[1]
        n_clusters = min(n_clusters, n_features)

        # Correlation-based distance and hierarchical clustering
        corr = np.corrcoef(X, rowvar=False)
        # Clamp to valid range for distance conversion
        corr = np.clip(corr, -1.0, 1.0)
        dist = ((1.0 - corr) / 2.0).clip(min=0.0)
        np.fill_diagonal(dist, 0.0)

        if n_features > 1:
            condensed = squareform(dist, checks=False)
            link = linkage(condensed, method="ward")
            labels = fcluster(link, t=n_clusters, criterion="maxclust")
        else:
            labels = np.array([1])

        rng = np.random.default_rng(42)
        baseline = float(accuracy_score(y, model.predict(X)))

        cluster_ids: list[int] = []
        cluster_features: list[str] = []
        cluster_importances: list[float] = []

        for cid in sorted(set(labels)):
            member_idx = np.where(labels == cid)[0]
            members = [feature_names[i] for i in member_idx]

            # Permute all features in the cluster
            drops: list[float] = []
            for _ in range(10):
                X_perm = X.copy()
                for idx in member_idx:
                    rng.shuffle(X_perm[:, idx])
                perm_score = float(accuracy_score(y, model.predict(X_perm)))
                drops.append(baseline - perm_score)

            cluster_ids.append(int(cid))
            cluster_features.append(", ".join(members))
            cluster_importances.append(float(np.mean(drops)))

        return pl.DataFrame(
            {
                "cluster": cluster_ids,
                "features": cluster_features,
                "importance": cluster_importances,
            }
        ).sort("importance", descending=True)
