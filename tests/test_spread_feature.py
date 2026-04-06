"""Tests for the SpreadFeature pairs trading implementation."""

from __future__ import annotations

import polars as pl
import pytest

from features.technical.spread import SpreadFeature


@pytest.fixture()
def feature() -> SpreadFeature:
    return SpreadFeature(ticker_a="AAPL", ticker_b="MSFT", hedge_ratio=1.5, window=5)


def _make_pair_df(close_a: list[float], close_b: list[float]) -> pl.DataFrame:
    return pl.DataFrame({"close_a": close_a, "close_b": close_b})


class TestSpreadCompute:
    def test_compute_adds_spread_and_zscore_columns(
        self, feature: SpreadFeature
    ) -> None:
        df = _make_pair_df([100.0] * 10, [60.0] * 10)
        result = feature.compute(df)
        assert "spread" in result.columns
        assert "spread_zscore" in result.columns

    def test_spread_formula(self, feature: SpreadFeature) -> None:
        close_a = [100.0, 110.0, 105.0, 120.0, 115.0]
        close_b = [50.0, 55.0, 52.0, 60.0, 58.0]
        hr = feature._hedge_ratio
        df = _make_pair_df(close_a, close_b)
        result = feature.compute(df)
        for i in range(len(close_a)):
            expected = close_a[i] - hr * close_b[i]
            assert result["spread"][i] == pytest.approx(expected)

    def test_spread_zscore_warmup_nulls(self, feature: SpreadFeature) -> None:
        df = _make_pair_df(list(range(1, 21)), list(range(21, 41)))
        result = feature.compute(df)
        warmup = result["spread_zscore"][: feature.lookback_days - 1]
        assert all(v is None for v in warmup.to_list())
        assert result["spread_zscore"][feature.lookback_days - 1] is not None

    def test_different_hedge_ratios_different_spreads(self) -> None:
        close_a = [100.0] * 10
        close_b = [60.0] * 10
        df = _make_pair_df(close_a, close_b)

        f1 = SpreadFeature("A", "B", hedge_ratio=1.0)
        f2 = SpreadFeature("A", "B", hedge_ratio=2.0)

        r1 = f1.compute(df)
        r2 = f2.compute(df)

        assert r1["spread"][0] == pytest.approx(100.0 - 1.0 * 60.0)
        assert r2["spread"][0] == pytest.approx(100.0 - 2.0 * 60.0)
        assert r1["spread"][0] != r2["spread"][0]


class TestSpreadProperties:
    def test_name_includes_tickers(self) -> None:
        f = SpreadFeature("AAPL", "MSFT", hedge_ratio=1.0)
        assert f.name == "spread_AAPL_MSFT"

    def test_category_is_technical(self, feature: SpreadFeature) -> None:
        assert feature.category == "technical"

    def test_lookback_days(self) -> None:
        for w in (5, 20, 60):
            f = SpreadFeature("A", "B", hedge_ratio=1.0, window=w)
            assert f.lookback_days == w
