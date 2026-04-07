"""Tests for models/training/cross_validation.py — purged K-fold CV."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.tree import DecisionTreeClassifier

from models.training.cross_validation import CVFold, PurgedKFoldCV


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _synthetic_data(
    n_samples: int = 200,
    n_features: int = 5,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Feature 0 is informative; features 1-4 are noise."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n_samples, n_features))
    y = (X[:, 0] > 0).astype(int)
    dates = np.arange(n_samples)  # ordinal "dates"
    return X, y, dates


# ---------------------------------------------------------------------------
# PurgedKFoldCV.split
# ---------------------------------------------------------------------------

class TestPurgedKFoldSplit:
    def test_split_returns_correct_number_of_folds(self) -> None:
        X, _, dates = _synthetic_data()
        cv = PurgedKFoldCV(n_splits=5, purge_window=3, embargo_pct=0.01)
        folds = cv.split(X, dates=dates)
        assert len(folds) == 5

    def test_no_overlap_between_train_and_test(self) -> None:
        X, _, dates = _synthetic_data()
        cv = PurgedKFoldCV(n_splits=5, purge_window=3, embargo_pct=0.01)
        for fold in cv.split(X, dates=dates):
            train_set = set(fold.train_indices.tolist())
            test_set = set(fold.test_indices.tolist())
            assert train_set.isdisjoint(test_set), "Train and test overlap"

    def test_purge_removes_boundary_samples(self) -> None:
        """Training indices must not include samples within purge_window
        of the test set boundaries."""
        n = 200
        purge_window = 5
        X, _, dates = _synthetic_data(n_samples=n)
        cv = PurgedKFoldCV(n_splits=5, purge_window=purge_window, embargo_pct=0.0)
        for fold in cv.split(X, dates=dates):
            test_min = int(fold.test_start)
            test_max = int(fold.test_end)
            purge_zone = set(
                range(
                    max(0, test_min - purge_window),
                    min(n, test_max + purge_window + 1),
                )
            )
            # Remove the test indices themselves from purge zone check
            purge_zone -= set(range(test_min, test_max + 1))
            train_set = set(fold.train_indices.tolist())
            leaked = train_set & purge_zone
            assert len(leaked) == 0, (
                f"Purge zone leaked {len(leaked)} samples into training"
            )

    def test_embargo_gap_after_test(self) -> None:
        """No training samples should appear in the embargo zone
        immediately after the test set."""
        n = 200
        embargo_pct = 0.05
        X, _, dates = _synthetic_data(n_samples=n)
        cv = PurgedKFoldCV(n_splits=5, purge_window=0, embargo_pct=embargo_pct)
        embargo_size = max(1, int(n * embargo_pct))
        for fold in cv.split(X, dates=dates):
            embargo_start = fold.test_end + 1
            embargo_end = min(n - 1, fold.test_end + embargo_size)
            embargo_zone = set(range(embargo_start, embargo_end + 1))
            train_set = set(fold.train_indices.tolist())
            leaked = train_set & embargo_zone
            assert len(leaked) == 0, (
                f"Embargo zone leaked {len(leaked)} samples into training"
            )

    def test_all_samples_used_in_test(self) -> None:
        """Union of all test folds should cover every index."""
        X, _, dates = _synthetic_data()
        cv = PurgedKFoldCV(n_splits=5, purge_window=0, embargo_pct=0.0)
        folds = cv.split(X, dates=dates)
        all_test = set()
        for fold in folds:
            all_test.update(fold.test_indices.tolist())
        assert all_test == set(range(len(X)))

    def test_temporal_ordering(self) -> None:
        """Test indices within each fold must be contiguous (not random)."""
        X, _, dates = _synthetic_data(n_samples=100)
        cv = PurgedKFoldCV(n_splits=5, purge_window=2, embargo_pct=0.01)
        for fold in cv.split(X, dates=dates):
            test = np.sort(fold.test_indices)
            diffs = np.diff(test)
            assert np.all(diffs == 1), "Test indices are not contiguous"


# ---------------------------------------------------------------------------
# PurgedKFoldCV.score
# ---------------------------------------------------------------------------

class TestPurgedKFoldScore:
    def test_score_returns_dict_with_required_keys(self) -> None:
        X, y, dates = _synthetic_data()
        cv = PurgedKFoldCV(n_splits=5, purge_window=2, embargo_pct=0.01)
        model = DecisionTreeClassifier(random_state=0)
        result = cv.score(model, X, y, dates=dates, metric="accuracy")
        assert "fold_scores" in result
        assert "mean_score" in result
        assert "std_score" in result

    def test_score_fold_count_matches_n_splits(self) -> None:
        X, y, dates = _synthetic_data()
        for n_splits in (3, 5, 7):
            cv = PurgedKFoldCV(n_splits=n_splits, purge_window=2, embargo_pct=0.01)
            model = DecisionTreeClassifier(random_state=0)
            result = cv.score(model, X, y, dates=dates, metric="accuracy")
            assert len(result["fold_scores"]) == n_splits

    def test_score_accuracy_reasonable(self) -> None:
        """With an informative feature the model should beat random."""
        X, y, _ = _synthetic_data(n_samples=500, seed=0)
        cv = PurgedKFoldCV(n_splits=5, purge_window=2, embargo_pct=0.01)
        model = DecisionTreeClassifier(random_state=0)
        result = cv.score(model, X, y, metric="accuracy")
        assert result["mean_score"] > 0.55

    def test_score_invalid_metric_raises(self) -> None:
        X, y, _ = _synthetic_data()
        cv = PurgedKFoldCV(n_splits=3)
        model = DecisionTreeClassifier(random_state=0)
        with pytest.raises(ValueError, match="metric must be"):
            cv.score(model, X, y, metric="f1")

    def test_score_auc_metric(self) -> None:
        X, y, _ = _synthetic_data(n_samples=500, seed=0)
        cv = PurgedKFoldCV(n_splits=5, purge_window=2, embargo_pct=0.01)
        model = DecisionTreeClassifier(random_state=0)
        result = cv.score(model, X, y, metric="auc")
        assert 0.0 <= result["mean_score"] <= 1.0
