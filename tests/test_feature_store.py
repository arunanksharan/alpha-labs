"""Tests for the FeatureStore (features/store.py)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from features.store import FeatureStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _business_dates(start: date, n: int) -> list[date]:
    dates: list[date] = []
    current = start
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def _make_feature_df(
    feature_col: str = "alpha_1",
    n: int = 100,
    start: date = date(2023, 1, 2),
    seed: int = 42,
) -> pl.DataFrame:
    """Create a simple feature DataFrame with date + one value column."""
    rng = np.random.default_rng(seed)
    dates = _business_dates(start, n)
    values = rng.normal(0.0, 1.0, size=n)
    return pl.DataFrame({
        "date": dates,
        feature_col: values.tolist(),
    }).with_columns(pl.col("date").cast(pl.Date))


def _make_ohlcv(n: int = 100, start: date = date(2023, 1, 2)) -> pl.DataFrame:
    """Minimal OHLCV for compute_and_store tests."""
    rng = np.random.default_rng(42)
    dates = _business_dates(start, n)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, size=n)))
    return pl.DataFrame({
        "date": dates,
        "open": close.tolist(),
        "high": (close * 1.01).tolist(),
        "low": (close * 0.99).tolist(),
        "close": close.tolist(),
        "volume": [1_000_000.0] * n,
    }).with_columns(pl.col("date").cast(pl.Date))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path: Path) -> FeatureStore:
    return FeatureStore(base_path=tmp_path / "store")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSaveAndLoad:

    def test_save_and_load_roundtrip(self, store: FeatureStore) -> None:
        df = _make_feature_df("momentum_20", n=50)
        rows = store.save("momentum_20", "AAPL", df)

        assert rows == 50

        loaded = store.load("momentum_20", "AAPL")
        assert loaded.height == 50
        assert "date" in loaded.columns
        assert "momentum_20" in loaded.columns
        # Values should match
        assert loaded["momentum_20"].to_list() == df["momentum_20"].to_list()

    def test_date_filtering(self, store: FeatureStore) -> None:
        df = _make_feature_df("rsi_14", n=100, start=date(2023, 1, 2))
        store.save("rsi_14", "MSFT", df)

        start = date(2023, 3, 1)
        end = date(2023, 4, 30)
        filtered = store.load("rsi_14", "MSFT", start=start, end=end)

        assert filtered.height > 0
        dates = filtered["date"].to_list()
        for d in dates:
            assert start <= d <= end

    def test_deduplication_on_save_twice(self, store: FeatureStore) -> None:
        df1 = _make_feature_df("vol_20", n=50, seed=1)
        df2 = _make_feature_df("vol_20", n=50, seed=2)  # same dates, different values

        store.save("vol_20", "GOOG", df1)
        rows = store.save("vol_20", "GOOG", df2)

        # After dedup on date, should still be 50 rows (not 100)
        assert rows == 50

        loaded = store.load("vol_20", "GOOG")
        assert loaded.height == 50
        # Values should be from the second write (keep="last")
        assert loaded["vol_20"].to_list() == df2["vol_20"].to_list()

    def test_missing_feature_returns_empty(self, store: FeatureStore) -> None:
        result = store.load("nonexistent_feature", "AAPL")
        assert isinstance(result, pl.DataFrame)
        assert result.is_empty()


class TestLoadMulti:

    def test_load_multi_joins_features(self, store: FeatureStore) -> None:
        df_a = _make_feature_df("alpha_1", n=60, seed=10)
        df_b = _make_feature_df("alpha_2", n=60, seed=20)

        store.save("alpha_1", "AAPL", df_a)
        store.save("alpha_2", "AAPL", df_b)

        combined = store.load_multi(["alpha_1", "alpha_2"], "AAPL")

        assert "date" in combined.columns
        assert "alpha_1" in combined.columns
        assert "alpha_2" in combined.columns
        assert combined.height == 60


class TestDiscovery:

    def test_list_features(self, store: FeatureStore) -> None:
        store.save("momentum_10", "AAPL", _make_feature_df("momentum_10", n=10))
        store.save("rsi_14", "AAPL", _make_feature_df("rsi_14", n=10))

        features = store.list_features()
        assert "momentum_10" in features
        assert "rsi_14" in features

    def test_list_tickers(self, store: FeatureStore) -> None:
        store.save("vol_20", "AAPL", _make_feature_df("vol_20", n=10))
        store.save("vol_20", "MSFT", _make_feature_df("vol_20", n=10))

        tickers = store.list_tickers("vol_20")
        assert "AAPL" in tickers
        assert "MSFT" in tickers
        assert len(tickers) == 2


class TestComputeAndStore:

    def test_compute_and_store(self, store: FeatureStore) -> None:
        from features.technical.zscore import ZScoreFeature

        feature = ZScoreFeature(window=20, price_col="close")
        ohlcv = _make_ohlcv(n=100)

        result = store.compute_and_store(feature, ohlcv, ticker="AAPL")

        # Result should have the zscore column
        assert "zscore" in result.columns
        assert result.height == 100

        # Feature should be persisted
        loaded = store.load("zscore_20", "AAPL")
        assert not loaded.is_empty()
        assert "zscore" in loaded.columns

    def test_compute_and_store_insufficient_data(self, store: FeatureStore) -> None:
        from features.technical.zscore import ZScoreFeature

        feature = ZScoreFeature(window=20, price_col="close")
        ohlcv = _make_ohlcv(n=10)  # too few rows

        with pytest.raises(ValueError, match="Insufficient data"):
            store.compute_and_store(feature, ohlcv, ticker="AAPL")


class TestStats:

    def test_get_stats(self, store: FeatureStore) -> None:
        store.save("feat_a", "AAPL", _make_feature_df("feat_a", n=20))
        store.save("feat_b", "MSFT", _make_feature_df("feat_b", n=30))

        stats = store.get_stats()
        assert stats["total_features"] == 2
        assert stats["total_files"] == 2
        assert stats["disk_bytes"] > 0
        assert stats["disk_mb"] >= 0
        assert "feat_a" in stats["features"]
        assert "feat_b" in stats["features"]


class TestQuery:

    def test_query_via_duckdb(self, store: FeatureStore) -> None:
        df = _make_feature_df("signal_1", n=50)
        store.save("signal_1", "AAPL", df)

        result = store.query("SELECT count(*) AS cnt FROM signal_1")
        assert result["cnt"].item() == 50

    def test_query_filter(self, store: FeatureStore) -> None:
        df = _make_feature_df("signal_2", n=80, start=date(2023, 1, 2))
        store.save("signal_2", "AAPL", df)

        result = store.query(
            "SELECT * FROM signal_2 WHERE date >= '2023-03-01'"
        )
        assert result.height > 0
        assert result.height < 80
