"""Tests for models/training/labeling.py — triple barrier & meta-labeling."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from models.training.labeling import TripleBarrierLabeler


# ---------------------------------------------------------------------------
# Helpers — synthetic price generators
# ---------------------------------------------------------------------------

def _business_dates(start: date, n: int) -> list[date]:
    dates: list[date] = []
    current = start
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def _uptrend_prices(n: int = 200, daily_return: float = 0.01) -> pl.DataFrame:
    """Constant uptrend: +daily_return per day."""
    dates = _business_dates(date(2022, 1, 3), n)
    close = 100.0 * np.exp(np.cumsum(np.full(n, daily_return)))
    return pl.DataFrame({"date": dates, "close": close.tolist()}).with_columns(
        pl.col("date").cast(pl.Date)
    )


def _downtrend_prices(n: int = 200, daily_return: float = -0.01) -> pl.DataFrame:
    """Constant downtrend: daily_return per day."""
    dates = _business_dates(date(2022, 1, 3), n)
    close = 100.0 * np.exp(np.cumsum(np.full(n, daily_return)))
    return pl.DataFrame({"date": dates, "close": close.tolist()}).with_columns(
        pl.col("date").cast(pl.Date)
    )


def _flat_prices(n: int = 200) -> pl.DataFrame:
    """Nearly flat prices with minimal noise."""
    rng = np.random.default_rng(42)
    dates = _business_dates(date(2022, 1, 3), n)
    # Tiny noise around 100
    close = 100.0 + rng.normal(0.0, 0.001, size=n).cumsum()
    return pl.DataFrame({"date": dates, "close": close.tolist()}).with_columns(
        pl.col("date").cast(pl.Date)
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def labeler() -> TripleBarrierLabeler:
    return TripleBarrierLabeler(
        profit_taking=2.0,
        stop_loss=2.0,
        max_holding_period=10,
        vol_window=20,
    )


@pytest.fixture()
def uptrend() -> pl.DataFrame:
    return _uptrend_prices()


@pytest.fixture()
def downtrend() -> pl.DataFrame:
    return _downtrend_prices()


@pytest.fixture()
def flat() -> pl.DataFrame:
    return _flat_prices()


# ---------------------------------------------------------------------------
# Tests — label()
# ---------------------------------------------------------------------------

class TestLabelOutputColumns:
    def test_label_output_columns(self, labeler: TripleBarrierLabeler, uptrend: pl.DataFrame) -> None:
        result = labeler.label(uptrend)
        expected_cols = {"date", "label", "barrier_hit", "return_at_barrier", "holding_period"}
        assert set(result.columns) == expected_cols


class TestLabelValuesInRange:
    def test_label_values_in_range(self, labeler: TripleBarrierLabeler, uptrend: pl.DataFrame) -> None:
        result = labeler.label(uptrend)
        unique_labels = set(result["label"].unique().to_list())
        assert unique_labels.issubset({-1, 0, 1})


class TestProfitTakingHit:
    def test_profit_taking_hit(self, labeler: TripleBarrierLabeler, uptrend: pl.DataFrame) -> None:
        """In a strong uptrend the upper barrier should be hit most often."""
        result = labeler.label(uptrend)
        n_upper = result.filter(pl.col("label") == 1).height
        # With 1% daily returns and 2x vol barriers, upper should dominate
        assert n_upper / result.height > 0.7, (
            f"Expected >70% upper hits in uptrend, got {n_upper}/{result.height}"
        )


class TestStopLossHit:
    def test_stop_loss_hit(self, labeler: TripleBarrierLabeler, downtrend: pl.DataFrame) -> None:
        """In a strong downtrend the lower barrier should be hit most often."""
        result = labeler.label(downtrend)
        n_lower = result.filter(pl.col("label") == -1).height
        assert n_lower / result.height > 0.7, (
            f"Expected >70% lower hits in downtrend, got {n_lower}/{result.height}"
        )


class TestTimeoutForFlatMarket:
    def test_timeout_for_flat_market(self) -> None:
        """With very wide barriers and flat prices, vertical barrier dominates."""
        flat = _flat_prices(n=300)
        wide_labeler = TripleBarrierLabeler(
            profit_taking=10.0,  # very wide
            stop_loss=10.0,      # very wide
            max_holding_period=5,
            vol_window=20,
        )
        result = wide_labeler.label(flat)
        n_vertical = result.filter(pl.col("label") == 0).height
        assert n_vertical / result.height > 0.7, (
            f"Expected >70% timeouts in flat market, got {n_vertical}/{result.height}"
        )


class TestHoldingPeriodBounded:
    def test_holding_period_bounded(self, labeler: TripleBarrierLabeler, uptrend: pl.DataFrame) -> None:
        result = labeler.label(uptrend)
        max_hp = result["holding_period"].max()
        assert max_hp <= labeler.max_holding_period


# ---------------------------------------------------------------------------
# Tests — meta_label()
# ---------------------------------------------------------------------------

class TestMetaLabelMatchesDirection:
    def test_meta_label_matches_direction(self, labeler: TripleBarrierLabeler) -> None:
        """When primary signal direction matches realized label, meta_label=1."""
        dates = _business_dates(date(2022, 6, 1), 5)
        primary = pl.DataFrame({
            "date": dates,
            "direction": [1, 1, -1, -1, 1],
        }).with_columns(pl.col("date").cast(pl.Date))

        labels = pl.DataFrame({
            "date": dates,
            "label": [1, 1, -1, -1, 1],
            "barrier_hit": ["upper"] * 5,
            "return_at_barrier": [0.02] * 5,
            "holding_period": [3] * 5,
        }).with_columns(pl.col("date").cast(pl.Date))

        result = labeler.meta_label(primary, labels)
        assert result["meta_label"].to_list() == [1, 1, 1, 1, 1]


class TestMetaLabelZeroOnMismatch:
    def test_meta_label_zero_on_mismatch(self, labeler: TripleBarrierLabeler) -> None:
        """When primary signal direction differs from realized label, meta_label=0."""
        dates = _business_dates(date(2022, 6, 1), 4)
        primary = pl.DataFrame({
            "date": dates,
            "direction": [1, -1, 1, -1],
        }).with_columns(pl.col("date").cast(pl.Date))

        labels = pl.DataFrame({
            "date": dates,
            "label": [-1, 1, 0, 0],
            "barrier_hit": ["lower", "upper", "vertical", "vertical"],
            "return_at_barrier": [-0.02, 0.02, 0.001, -0.001],
            "holding_period": [3, 3, 10, 10],
        }).with_columns(pl.col("date").cast(pl.Date))

        result = labeler.meta_label(primary, labels)
        assert result["meta_label"].to_list() == [0, 0, 0, 0]


# ---------------------------------------------------------------------------
# Tests — compute_sample_weights()
# ---------------------------------------------------------------------------

class TestSampleWeightsSumReasonable:
    def test_sample_weights_sum_reasonable(
        self, labeler: TripleBarrierLabeler, uptrend: pl.DataFrame
    ) -> None:
        labels = labeler.label(uptrend)
        weights = labeler.compute_sample_weights(labels, uptrend)
        assert "weight" in weights.columns
        total = weights["weight"].sum()
        n = weights.height
        # Weights are normalized to sum to n
        assert abs(total - n) < 1e-6, f"Expected weights to sum to {n}, got {total}"


class TestSampleWeightsAllPositive:
    def test_sample_weights_all_positive(
        self, labeler: TripleBarrierLabeler, uptrend: pl.DataFrame
    ) -> None:
        labels = labeler.label(uptrend)
        weights = labeler.compute_sample_weights(labels, uptrend)
        assert (weights["weight"] > 0).all(), "All sample weights must be positive"
