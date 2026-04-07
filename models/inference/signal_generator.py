"""ML-based signal generation pipeline.

Wraps any sklearn-compatible estimator to produce :class:`Signal` objects,
supporting walk-forward training with purged cross-validation.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import polars as pl

from core.strategies import Signal
from models.training.cross_validation import PurgedKFoldCV

logger = logging.getLogger(__name__)


class MLSignalGenerator:
    """Generate trading signals from ML model predictions.

    Wraps any sklearn-compatible model to produce Signal objects.
    Supports walk-forward training with purged CV.

    Parameters
    ----------
    model
        Any estimator exposing `fit`, `predict`, and optionally
        `predict_proba` (sklearn interface).
    feature_names
        Column names to extract from a features DataFrame.  If *None* all
        columns except ``date`` and ``ticker`` are used.
    cv
        Optional :class:`PurgedKFoldCV` instance for validation during fit.
    prediction_threshold
        Probability threshold for generating directional signals.
    """

    def __init__(
        self,
        model: Any,
        feature_names: list[str] | None = None,
        cv: PurgedKFoldCV | None = None,
        prediction_threshold: float = 0.5,
    ) -> None:
        self.model = model
        self.feature_names = feature_names
        self.cv = cv
        self.prediction_threshold = prediction_threshold
        self._is_fitted: bool = False

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit the underlying model.

        If *cv* was provided at init, run purged cross-validation first and
        log the fold scores before fitting on the full dataset.
        """
        if self.cv is not None:
            folds = self.cv.split(X)
            scores: list[float] = []
            for fold in folds:
                X_train = X[fold.train_indices]
                y_train = y[fold.train_indices]
                X_test = X[fold.test_indices]
                y_test = y[fold.test_indices]
                self.model.fit(X_train, y_train)
                score = float(self.model.score(X_test, y_test))
                scores.append(score)
                logger.info(
                    "CV fold score: %.4f (train %d-%d, test %d-%d)",
                    score,
                    fold.train_start,
                    fold.train_end,
                    fold.test_start,
                    fold.test_end,
                )
            logger.info(
                "CV mean score: %.4f (+/- %.4f)",
                float(np.mean(scores)),
                float(np.std(scores)),
            )

        # Fit on full dataset
        self.model.fit(X, y)
        self._is_fitted = True

    # ------------------------------------------------------------------
    # Prediction helpers
    # ------------------------------------------------------------------

    def _resolve_feature_names(self, features: pl.DataFrame) -> list[str]:
        """Return feature column names, excluding date and ticker."""
        if self.feature_names is not None:
            return self.feature_names
        return [c for c in features.columns if c not in ("date", "ticker")]

    def _get_predictions(self, X: np.ndarray) -> np.ndarray:
        """Return prediction probabilities (class-1) when available."""
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(X)
            # Return probability of the positive class (column 1)
            return proba[:, 1] if proba.ndim == 2 else proba
        return self.model.predict(X).astype(float)

    def _predictions_to_signals(
        self,
        predictions: np.ndarray,
        dates: list[str],
        tickers: list[str],
    ) -> list[Signal]:
        """Convert raw prediction array to a list of Signal objects."""
        signals: list[Signal] = []
        threshold = self.prediction_threshold

        for pred, dt, ticker in zip(predictions, dates, tickers, strict=True):
            if pred > threshold:
                signals.append(
                    Signal(
                        ticker=ticker,
                        date=dt,
                        direction=1.0,
                        confidence=float(pred),
                    )
                )
            elif pred < (1.0 - threshold):
                signals.append(
                    Signal(
                        ticker=ticker,
                        date=dt,
                        direction=-1.0,
                        confidence=float(1.0 - pred),
                    )
                )
            # else: no signal (ambiguous prediction)

        return signals

    # ------------------------------------------------------------------
    # Public prediction methods
    # ------------------------------------------------------------------

    def predict(self, features: pl.DataFrame) -> list[Signal]:
        """Generate signals from a features DataFrame.

        Parameters
        ----------
        features
            Must contain ``date``, ``ticker``, and feature columns.

        Returns
        -------
        list[Signal]
            One signal per row that exceeds the prediction threshold.
        """
        if features.is_empty():
            return []

        feat_cols = self._resolve_feature_names(features)
        X = features.select(feat_cols).to_numpy()
        predictions = self._get_predictions(X)

        dates = features["date"].cast(pl.Utf8).to_list()
        tickers = features["ticker"].to_list()

        return self._predictions_to_signals(predictions, dates, tickers)

    def walk_forward_predict(
        self,
        features: pl.DataFrame,
        labels: pl.Series,
        train_window: int = 252,
        test_window: int = 63,
    ) -> list[Signal]:
        """Walk-forward out-of-sample signal generation.

        Uses an expanding window: trains on ``[0 : t]``, predicts on
        ``[t : t + test_window]``.  All returned signals are strictly
        out-of-sample.

        Parameters
        ----------
        features
            DataFrame with ``date``, ``ticker``, and feature columns.
        labels
            Target variable aligned with *features* rows.
        train_window
            Minimum number of rows before the first prediction step.
        test_window
            Number of rows to predict in each step.

        Returns
        -------
        list[Signal]
            Accumulated out-of-sample signals.
        """
        if features.is_empty():
            return []

        feat_cols = self._resolve_feature_names(features)
        n = len(features)
        all_signals: list[Signal] = []

        t = train_window
        while t < n:
            test_end = min(t + test_window, n)

            # Train on [0, t)
            train_df = features.slice(0, t)
            X_train = train_df.select(feat_cols).to_numpy()
            y_train = labels.slice(0, t).to_numpy()
            self.model.fit(X_train, y_train)
            self._is_fitted = True

            # Predict on [t, test_end)
            test_df = features.slice(t, test_end - t)
            X_test = test_df.select(feat_cols).to_numpy()
            predictions = self._get_predictions(X_test)

            dates = test_df["date"].cast(pl.Utf8).to_list()
            tickers = test_df["ticker"].to_list()
            all_signals.extend(
                self._predictions_to_signals(predictions, dates, tickers)
            )

            t = test_end

        return all_signals

    def ensemble_predict(
        self,
        features: pl.DataFrame,
        models: list[Any],
        weights: list[float] | None = None,
    ) -> list[Signal]:
        """Generate signals by averaging predictions from multiple models.

        Parameters
        ----------
        features
            DataFrame with ``date``, ``ticker``, and feature columns.
        models
            List of fitted sklearn-compatible estimators.
        weights
            Optional weights for weighted average.  Must sum to 1 (or will
            be normalised).  If *None*, equal weighting is used.

        Returns
        -------
        list[Signal]
        """
        if features.is_empty():
            return []

        feat_cols = self._resolve_feature_names(features)
        X = features.select(feat_cols).to_numpy()

        if weights is None:
            weights = [1.0 / len(models)] * len(models)
        else:
            total = sum(weights)
            weights = [w / total for w in weights]

        # Weighted average of predictions
        avg_predictions = np.zeros(len(X), dtype=float)
        for model, w in zip(models, weights, strict=True):
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X)
                preds = proba[:, 1] if proba.ndim == 2 else proba
            else:
                preds = model.predict(X).astype(float)
            avg_predictions += w * preds

        dates = features["date"].cast(pl.Utf8).to_list()
        tickers = features["ticker"].to_list()

        return self._predictions_to_signals(avg_predictions, dates, tickers)
