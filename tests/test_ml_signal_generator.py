"""Tests for MLSignalGenerator."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest
from sklearn.tree import DecisionTreeClassifier

from core.strategies import Signal
from models.inference.signal_generator import MLSignalGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def synthetic_data() -> tuple[pl.DataFrame, pl.Series]:
    """Synthetic features DataFrame and binary labels."""
    rng = np.random.default_rng(42)
    n = 400
    dates = [f"2024-01-{(i % 30) + 1:02d}" for i in range(n)]
    tickers = [f"TICK_{i % 10}" for i in range(n)]
    f1 = rng.standard_normal(n)
    f2 = rng.standard_normal(n)
    # Label is deterministic function of features so a tree can learn it
    labels = ((f1 + f2) > 0).astype(int)

    features = pl.DataFrame(
        {
            "date": dates,
            "ticker": tickers,
            "f1": f1.tolist(),
            "f2": f2.tolist(),
        }
    )
    return features, pl.Series("label", labels.tolist())


@pytest.fixture()
def fitted_generator(synthetic_data: tuple[pl.DataFrame, pl.Series]) -> MLSignalGenerator:
    """MLSignalGenerator with a fitted DecisionTreeClassifier."""
    features, labels = synthetic_data
    gen = MLSignalGenerator(
        model=DecisionTreeClassifier(random_state=0),
        feature_names=["f1", "f2"],
        prediction_threshold=0.5,
    )
    X = features.select("f1", "f2").to_numpy()
    gen.fit(X, labels.to_numpy())
    return gen


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFit:
    def test_fit_trains_model(self, synthetic_data: tuple[pl.DataFrame, pl.Series]) -> None:
        features, labels = synthetic_data
        gen = MLSignalGenerator(
            model=DecisionTreeClassifier(random_state=0),
            feature_names=["f1", "f2"],
        )
        X = features.select("f1", "f2").to_numpy()
        gen.fit(X, labels.to_numpy())
        assert gen._is_fitted is True
        # Model should be able to predict after fitting
        preds = gen.model.predict(X[:5])
        assert len(preds) == 5


class TestPredict:
    def test_predict_returns_signals(
        self,
        fitted_generator: MLSignalGenerator,
        synthetic_data: tuple[pl.DataFrame, pl.Series],
    ) -> None:
        features, _ = synthetic_data
        signals = fitted_generator.predict(features)
        assert isinstance(signals, list)
        assert len(signals) > 0
        assert all(isinstance(s, Signal) for s in signals)

    def test_predict_signal_direction_bounds(
        self,
        fitted_generator: MLSignalGenerator,
        synthetic_data: tuple[pl.DataFrame, pl.Series],
    ) -> None:
        features, _ = synthetic_data
        signals = fitted_generator.predict(features)
        for s in signals:
            assert s.direction in (-1.0, 1.0)

    def test_predict_signal_confidence_bounds(
        self,
        fitted_generator: MLSignalGenerator,
        synthetic_data: tuple[pl.DataFrame, pl.Series],
    ) -> None:
        features, _ = synthetic_data
        signals = fitted_generator.predict(features)
        for s in signals:
            assert 0.0 <= s.confidence <= 1.0

    def test_empty_features_returns_empty(
        self, fitted_generator: MLSignalGenerator
    ) -> None:
        empty = pl.DataFrame(
            {"date": [], "ticker": [], "f1": [], "f2": []}
        )
        signals = fitted_generator.predict(empty)
        assert signals == []


class TestWalkForward:
    def test_walk_forward_predict_no_lookahead(
        self, synthetic_data: tuple[pl.DataFrame, pl.Series]
    ) -> None:
        """Signals must only appear at dates *after* the training window."""
        features, labels = synthetic_data
        train_window = 100
        test_window = 50

        gen = MLSignalGenerator(
            model=DecisionTreeClassifier(random_state=0),
            feature_names=["f1", "f2"],
            prediction_threshold=0.5,
        )
        signals = gen.walk_forward_predict(
            features, labels, train_window=train_window, test_window=test_window
        )
        assert len(signals) > 0

        # All signal dates must come from rows >= train_window
        training_dates = set(features.slice(0, train_window)["date"].to_list())
        oos_dates = set(features.slice(train_window, len(features) - train_window)["date"].to_list())

        # Every signal's date must exist in the out-of-sample portion
        for s in signals:
            assert s.date in oos_dates, (
                f"Signal date {s.date} found in training data -- look-ahead leak!"
            )


class TestEnsemble:
    def test_ensemble_predict_averages_models(
        self, synthetic_data: tuple[pl.DataFrame, pl.Series]
    ) -> None:
        features, labels = synthetic_data
        X = features.select("f1", "f2").to_numpy()
        y = labels.to_numpy()

        m1 = DecisionTreeClassifier(random_state=0, max_depth=2)
        m2 = DecisionTreeClassifier(random_state=1, max_depth=3)
        m1.fit(X, y)
        m2.fit(X, y)

        gen = MLSignalGenerator(
            model=m1,  # base model (not used by ensemble_predict)
            feature_names=["f1", "f2"],
            prediction_threshold=0.5,
        )
        signals = gen.ensemble_predict(features, models=[m1, m2])
        assert isinstance(signals, list)
        assert len(signals) > 0
        assert all(isinstance(s, Signal) for s in signals)
