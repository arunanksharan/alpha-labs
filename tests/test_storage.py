"""Tests for data/storage/store.py — DataStore public API."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from data.storage.store import DataStore, _coerce_date, _normalize_ticker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path: Path) -> DataStore:
    return DataStore(base_path=tmp_path / "store")


def _ohlcv(
    start_day: int = 2,
    n: int = 10,
    year: int = 2023,
    month: int = 1,
) -> pl.DataFrame:
    days = list(range(start_day, start_day + n))
    dates = [date(year, month, d) for d in days]
    return pl.DataFrame(
        {
            "date": dates,
            "open": [100.0 + i for i in range(n)],
            "high": [102.0 + i for i in range(n)],
            "low": [98.0 + i for i in range(n)],
            "close": [101.0 + i for i in range(n)],
            "volume": [1_000_000.0] * n,
        }
    ).with_columns(pl.col("date").cast(pl.Date))


def _macro(n: int = 10) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date(2023, 1, i) for i in range(1, n + 1)],
            "value": [5.0 + i * 0.1 for i in range(n)],
        }
    ).with_columns(pl.col("date").cast(pl.Date))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestNormalizeTicker:
    @pytest.mark.parametrize("raw,expected", [
        ("aapl", "AAPL"),
        ("BRK/B", "BRK_B"),
        ("  tsla  ", "TSLA"),
        ("msft", "MSFT"),
    ])
    def test_normalization(self, raw: str, expected: str) -> None:
        assert _normalize_ticker(raw) == expected


class TestCoerceDate:
    def test_date_passthrough(self) -> None:
        d = date(2023, 6, 15)
        assert _coerce_date(d) == d

    def test_none_passthrough(self) -> None:
        assert _coerce_date(None) is None

    @pytest.mark.parametrize("s", ["2023-06-15", "20230615", "2023/06/15"])
    def test_string_formats(self, s: str) -> None:
        assert _coerce_date(s) == date(2023, 6, 15)

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError):
            _coerce_date("not-a-date")

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError):
            _coerce_date(20230615)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# OHLCV: save / load round-trip
# ---------------------------------------------------------------------------

class TestOhlcvRoundTrip:
    def test_basic_roundtrip(self, store: DataStore) -> None:
        data = _ohlcv()
        rows = store.save_ohlcv("AAPL", data, source="test")
        assert rows == 10
        loaded = store.load_ohlcv("AAPL")
        assert len(loaded) == 10
        assert set(["open", "high", "low", "close", "volume"]).issubset(loaded.columns)

    def test_ticker_case_insensitive(self, store: DataStore) -> None:
        store.save_ohlcv("aapl", _ohlcv(), source="test")
        assert not store.load_ohlcv("AAPL").is_empty()
        assert not store.load_ohlcv("aapl").is_empty()

    def test_ticker_slash_normalized(self, store: DataStore) -> None:
        store.save_ohlcv("BRK/B", _ohlcv(), source="test")
        assert not store.load_ohlcv("BRK/B").is_empty()

    def test_source_and_ticker_columns_attached(self, store: DataStore) -> None:
        store.save_ohlcv("MSFT", _ohlcv(), source="yfinance", interval="1d")
        loaded = store.load_ohlcv("MSFT")
        assert loaded["source"][0] == "yfinance"
        assert loaded["ticker"][0] == "MSFT"

    def test_interval_column_attached(self, store: DataStore) -> None:
        store.save_ohlcv("NVDA", _ohlcv(), source="test", interval="1h")
        loaded = store.load_ohlcv("NVDA", interval="1h")
        assert loaded["interval"][0] == "1h"

    def test_missing_ticker_returns_empty_df(self, store: DataStore) -> None:
        result = store.load_ohlcv("NONEXISTENT")
        assert result.is_empty()

    def test_missing_interval_returns_empty_df(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(), source="test", interval="1d")
        result = store.load_ohlcv("AAPL", interval="1h")
        assert result.is_empty()

    def test_values_preserved(self, store: DataStore) -> None:
        data = _ohlcv()
        store.save_ohlcv("GOOG", data, source="test")
        loaded = store.load_ohlcv("GOOG").sort("date")
        original = data.sort("date")
        assert loaded["close"].to_list() == original["close"].to_list()

    def test_date_column_present_in_output(self, store: DataStore) -> None:
        store.save_ohlcv("AMZN", _ohlcv(), source="test")
        loaded = store.load_ohlcv("AMZN")
        assert "date" in loaded.columns

    def test_data_sorted_by_date_after_save(self, store: DataStore) -> None:
        data = _ohlcv()
        store.save_ohlcv("TSLA", data, source="test")
        loaded = store.load_ohlcv("TSLA")
        dates = loaded["date"].to_list()
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# OHLCV: date filtering
# ---------------------------------------------------------------------------

class TestOhlcvDateFiltering:
    def test_start_filter(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(start_day=2, n=10), source="test")
        loaded = store.load_ohlcv("AAPL", start=date(2023, 1, 7))
        assert all(d >= date(2023, 1, 7) for d in loaded["date"].to_list())

    def test_end_filter(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(start_day=2, n=10), source="test")
        loaded = store.load_ohlcv("AAPL", end=date(2023, 1, 6))
        assert all(d <= date(2023, 1, 6) for d in loaded["date"].to_list())

    def test_start_and_end_filter(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(start_day=2, n=10), source="test")
        loaded = store.load_ohlcv("AAPL", start=date(2023, 1, 5), end=date(2023, 1, 8))
        assert len(loaded) == 4

    def test_string_date_filter(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(start_day=2, n=10), source="test")
        loaded = store.load_ohlcv("AAPL", start="2023-01-05", end="2023-01-08")
        assert len(loaded) == 4

    def test_filter_beyond_range_returns_empty(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(start_day=2, n=10), source="test")
        loaded = store.load_ohlcv("AAPL", start=date(2025, 1, 1))
        assert loaded.is_empty()


# ---------------------------------------------------------------------------
# OHLCV: deduplication on merge
# ---------------------------------------------------------------------------

class TestOhlcvDeduplication:
    def test_save_twice_no_duplicates(self, store: DataStore) -> None:
        data = _ohlcv()
        store.save_ohlcv("AAPL", data, source="test")
        store.save_ohlcv("AAPL", data, source="test")
        loaded = store.load_ohlcv("AAPL")
        assert len(loaded) == 10

    def test_save_overlapping_data_deduplicates(self, store: DataStore) -> None:
        first_batch = _ohlcv(start_day=2, n=10)
        second_batch = _ohlcv(start_day=7, n=10)
        store.save_ohlcv("AAPL", first_batch, source="test")
        store.save_ohlcv("AAPL", second_batch, source="test")
        loaded = store.load_ohlcv("AAPL")
        dates = loaded["date"].to_list()
        assert len(dates) == len(set(dates))

    def test_newer_write_wins_on_dedup(self, store: DataStore) -> None:
        original = pl.DataFrame(
            {"date": [date(2023, 1, 2)], "open": [100.0], "high": [102.0],
             "low": [98.0], "close": [101.0], "volume": [1e6]}
        ).with_columns(pl.col("date").cast(pl.Date))
        updated = pl.DataFrame(
            {"date": [date(2023, 1, 2)], "open": [999.0], "high": [999.0],
             "low": [999.0], "close": [999.0], "volume": [999.0]}
        ).with_columns(pl.col("date").cast(pl.Date))
        store.save_ohlcv("AAPL", original, source="test")
        store.save_ohlcv("AAPL", updated, source="test")
        loaded = store.load_ohlcv("AAPL")
        assert len(loaded) == 1
        assert loaded["close"][0] == 999.0

    def test_save_returns_row_count(self, store: DataStore) -> None:
        rows = store.save_ohlcv("AAPL", _ohlcv(n=20), source="test")
        assert rows == 20


# ---------------------------------------------------------------------------
# Macro: save / load round-trip
# ---------------------------------------------------------------------------

class TestMacroRoundTrip:
    def test_basic_roundtrip(self, store: DataStore) -> None:
        store.save_macro("DFF", _macro(10))
        loaded = store.load_macro("DFF")
        assert len(loaded) == 10

    def test_series_id_uppercased(self, store: DataStore) -> None:
        store.save_macro("dff", _macro(5))
        loaded = store.load_macro("DFF")
        assert not loaded.is_empty()

    def test_series_id_column_attached(self, store: DataStore) -> None:
        store.save_macro("GDP", _macro(5))
        loaded = store.load_macro("GDP")
        assert loaded["series_id"][0] == "GDP"

    def test_missing_series_returns_empty(self, store: DataStore) -> None:
        assert store.load_macro("NONEXISTENT").is_empty()

    def test_date_filter_start(self, store: DataStore) -> None:
        store.save_macro("CPI", _macro(10))
        loaded = store.load_macro("CPI", start=date(2023, 1, 5))
        assert all(d >= date(2023, 1, 5) for d in loaded["date"].to_list())

    def test_date_filter_end(self, store: DataStore) -> None:
        store.save_macro("CPI", _macro(10))
        loaded = store.load_macro("CPI", end=date(2023, 1, 5))
        assert all(d <= date(2023, 1, 5) for d in loaded["date"].to_list())

    def test_date_filter_range(self, store: DataStore) -> None:
        store.save_macro("DGS10", _macro(10))
        loaded = store.load_macro("DGS10", start=date(2023, 1, 3), end=date(2023, 1, 7))
        assert len(loaded) == 5

    def test_deduplication_on_double_save(self, store: DataStore) -> None:
        store.save_macro("FEDFUNDS", _macro(10))
        store.save_macro("FEDFUNDS", _macro(10))
        loaded = store.load_macro("FEDFUNDS")
        assert len(loaded) == 10


# ---------------------------------------------------------------------------
# Discovery: list_tickers, list_date_range, get_stats
# ---------------------------------------------------------------------------

class TestDiscovery:
    def test_list_tickers_empty_store(self, store: DataStore) -> None:
        assert store.list_tickers() == []

    def test_list_tickers_after_saves(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(), source="test")
        store.save_ohlcv("MSFT", _ohlcv(), source="test")
        tickers = store.list_tickers()
        assert "AAPL" in tickers
        assert "MSFT" in tickers

    def test_list_tickers_sorted(self, store: DataStore) -> None:
        for t in ("TSLA", "AAPL", "MSFT"):
            store.save_ohlcv(t, _ohlcv(), source="test")
        tickers = store.list_tickers()
        assert tickers == sorted(tickers)

    def test_list_tickers_no_duplicates(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(), source="test")
        store.save_ohlcv("AAPL", _ohlcv(), source="test")
        assert store.list_tickers().count("AAPL") == 1

    def test_list_date_range_correct_bounds(self, store: DataStore) -> None:
        store.save_ohlcv("GOOG", _ohlcv(start_day=2, n=10), source="test")
        min_d, max_d = store.list_date_range("GOOG")
        assert min_d == date(2023, 1, 2)
        assert max_d == date(2023, 1, 11)

    def test_list_date_range_missing_ticker(self, store: DataStore) -> None:
        min_d, max_d = store.list_date_range("NONEXISTENT")
        assert min_d is None
        assert max_d is None

    def test_get_stats_structure(self, store: DataStore) -> None:
        store.save_ohlcv("META", _ohlcv(), source="test")
        stats = store.get_stats()
        assert "base_path" in stats
        assert "parquet_files" in stats
        assert "total_rows" in stats
        assert "parquet_disk_bytes" in stats
        assert "tickers" in stats
        assert "categories" in stats

    def test_get_stats_row_count(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(n=15), source="test")
        stats = store.get_stats()
        assert stats["total_rows"] >= 15

    def test_get_stats_ticker_count(self, store: DataStore) -> None:
        for t in ("AAPL", "MSFT", "GOOG"):
            store.save_ohlcv(t, _ohlcv(), source="test")
        stats = store.get_stats()
        assert stats["tickers"] >= 3

    def test_get_stats_categories_ohlcv_count(self, store: DataStore) -> None:
        store.save_ohlcv("NVDA", _ohlcv(), source="test")
        stats = store.get_stats()
        assert stats["categories"]["ohlcv"] >= 1


# ---------------------------------------------------------------------------
# Directory isolation: each tmp_path is independent
# ---------------------------------------------------------------------------

class TestIsolation:
    def test_stores_are_isolated(self, tmp_path: Path) -> None:
        store_a = DataStore(base_path=tmp_path / "a")
        store_b = DataStore(base_path=tmp_path / "b")
        store_a.save_ohlcv("AAPL", _ohlcv(), source="test")
        assert store_b.load_ohlcv("AAPL").is_empty()

    def test_repr_contains_base_path(self, store: DataStore) -> None:
        r = repr(store)
        assert "DataStore" in r

    def test_multiple_intervals_stored_separately(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(), source="test", interval="1d")
        store.save_ohlcv("AAPL", _ohlcv(), source="test", interval="1h")
        d = store.load_ohlcv("AAPL", interval="1d")
        h = store.load_ohlcv("AAPL", interval="1h")
        assert not d.is_empty()
        assert not h.is_empty()


# ---------------------------------------------------------------------------
# Vacuum
# ---------------------------------------------------------------------------

class TestVacuum:
    def test_vacuum_preserves_data(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(), source="test")
        store.vacuum()
        loaded = store.load_ohlcv("AAPL")
        assert len(loaded) == 10

    def test_vacuum_on_empty_store_does_not_raise(self, store: DataStore) -> None:
        store.vacuum()


# ---------------------------------------------------------------------------
# DuckDB query interface
# ---------------------------------------------------------------------------

class TestDuckDBQuery:
    def test_count_query(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(n=10), source="test")
        result = store.query("SELECT count(*) AS cnt FROM ohlcv")
        assert result["cnt"][0] >= 10

    def test_filter_query(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(n=10), source="test")
        result = store.query("SELECT * FROM ohlcv WHERE ticker = 'AAPL'")
        assert len(result) >= 10

    def test_query_returns_polars_df(self, store: DataStore) -> None:
        store.save_ohlcv("AAPL", _ohlcv(n=5), source="test")
        result = store.query("SELECT * FROM ohlcv LIMIT 1")
        assert isinstance(result, pl.DataFrame)
