"""Tests for models/training/feature_importance.py — MDI, MDA, SFI."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

from models.training.cross_validation import PurgedKFoldCV
from models.training.feature_importance import FeatureImportance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FEATURE_NAMES = ["informative", "noise_1", "noise_2", "noise_3", "noise_4"]


def _synthetic_data(
    n_samples: int = 500,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Feature 0 is informative; features 1-4 are pure noise."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n_samples, 5))
    # Make feature 0 strongly predictive
    y = (X[:, 0] > 0).astype(int)
    return X, y


def _fitted_tree(X: np.ndarray, y: np.ndarray) -> DecisionTreeClassifier:
    model = DecisionTreeClassifier(random_state=0)
    model.fit(X, y)
    return model


def _fitted_forest(X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
    model = RandomForestClassifier(n_estimators=30, random_state=0)
    model.fit(X, y)
    return model


# ---------------------------------------------------------------------------
# MDI tests
# ---------------------------------------------------------------------------

class TestMDI:
    def test_mdi_returns_dataframe_with_correct_schema(self) -> None:
        X, y = _synthetic_data()
        model = _fitted_forest(X, y)
        fi = FeatureImportance()
        result = fi.mdi(model, FEATURE_NAMES)
        assert isinstance(result, pl.DataFrame)
        assert set(result.columns) == {"feature", "importance", "rank"}
        assert len(result) == len(FEATURE_NAMES)

    def test_mdi_importance_sums_to_one(self) -> None:
        X, y = _synthetic_data()
        model = _fitted_forest(X, y)
        fi = FeatureImportance()
        result = fi.mdi(model, FEATURE_NAMES)
        total = result["importance"].sum()
        assert abs(total - 1.0) < 1e-6

    def test_mdi_informative_feature_ranks_first(self) -> None:
        X, y = _synthetic_data()
        model = _fitted_forest(X, y)
        fi = FeatureImportance()
        result = fi.mdi(model, FEATURE_NAMES)
        top_feature = result.sort("importance", descending=True)["feature"][0]
        assert top_feature == "informative"

    def test_mdi_mismatched_names_raises(self) -> None:
        X, y = _synthetic_data()
        model = _fitted_forest(X, y)
        fi = FeatureImportance()
        with pytest.raises(ValueError, match="names were provided"):
            fi.mdi(model, ["a", "b"])


# ---------------------------------------------------------------------------
# MDA tests
# ---------------------------------------------------------------------------

class TestMDA:
    def test_mda_returns_dataframe_with_correct_schema(self) -> None:
        X, y = _synthetic_data()
        model = _fitted_forest(X, y)
        fi = FeatureImportance()
        result = fi.mda(model, X, y, FEATURE_NAMES, n_repeats=5)
        assert isinstance(result, pl.DataFrame)
        assert set(result.columns) == {"feature", "importance", "importance_std", "rank"}
        assert len(result) == len(FEATURE_NAMES)

    def test_mda_informative_feature_ranks_high(self) -> None:
        X, y = _synthetic_data()
        model = _fitted_forest(X, y)
        fi = FeatureImportance()
        result = fi.mda(model, X, y, FEATURE_NAMES, n_repeats=10)
        # The informative feature should be ranked 1
        informative_row = result.filter(pl.col("feature") == "informative")
        assert informative_row["rank"][0] == 1

    def test_mda_informative_importance_positive(self) -> None:
        X, y = _synthetic_data()
        model = _fitted_forest(X, y)
        fi = FeatureImportance()
        result = fi.mda(model, X, y, FEATURE_NAMES, n_repeats=10)
        informative_row = result.filter(pl.col("feature") == "informative")
        assert informative_row["importance"][0] > 0.0


# ---------------------------------------------------------------------------
# SFI tests
# ---------------------------------------------------------------------------

class TestSFI:
    def test_sfi_returns_dataframe_with_correct_schema(self) -> None:
        X, y = _synthetic_data(n_samples=200)
        cv = PurgedKFoldCV(n_splits=3, purge_window=2, embargo_pct=0.01)
        fi = FeatureImportance(cv=cv)

        def factory() -> DecisionTreeClassifier:
            return DecisionTreeClassifier(random_state=0)

        result = fi.sfi(factory, X, y, FEATURE_NAMES)
        assert isinstance(result, pl.DataFrame)
        assert set(result.columns) == {"feature", "importance", "rank"}
        assert len(result) == len(FEATURE_NAMES)

    def test_sfi_informative_feature_ranks_high(self) -> None:
        X, y = _synthetic_data(n_samples=500)
        cv = PurgedKFoldCV(n_splits=3, purge_window=2, embargo_pct=0.01)
        fi = FeatureImportance(cv=cv)

        def factory() -> DecisionTreeClassifier:
            return DecisionTreeClassifier(random_state=0)

        result = fi.sfi(factory, X, y, FEATURE_NAMES)
        top_feature = result.sort("importance", descending=True)["feature"][0]
        assert top_feature == "informative"

    def test_sfi_importance_values_are_bounded(self) -> None:
        X, y = _synthetic_data(n_samples=200)
        cv = PurgedKFoldCV(n_splits=3, purge_window=2, embargo_pct=0.01)
        fi = FeatureImportance(cv=cv)

        def factory() -> DecisionTreeClassifier:
            return DecisionTreeClassifier(random_state=0)

        result = fi.sfi(factory, X, y, FEATURE_NAMES)
        # Accuracy scores should be between 0 and 1
        assert result["importance"].min() >= 0.0
        assert result["importance"].max() <= 1.0


# ---------------------------------------------------------------------------
# Clustered importance tests
# ---------------------------------------------------------------------------

class TestClusteredImportance:
    def test_clustered_returns_dataframe(self) -> None:
        X, y = _synthetic_data()
        model = _fitted_forest(X, y)
        fi = FeatureImportance()
        result = fi.clustered_importance(model, X, y, FEATURE_NAMES, n_clusters=3)
        assert isinstance(result, pl.DataFrame)
        assert set(result.columns) == {"cluster", "features", "importance"}
        assert len(result) <= 3

    def test_clustered_all_features_present(self) -> None:
        X, y = _synthetic_data()
        model = _fitted_forest(X, y)
        fi = FeatureImportance()
        result = fi.clustered_importance(model, X, y, FEATURE_NAMES, n_clusters=3)
        # Every feature name should appear exactly once across all clusters
        all_features = set()
        for row in result["features"].to_list():
            for name in row.split(", "):
                all_features.add(name)
        assert all_features == set(FEATURE_NAMES)
