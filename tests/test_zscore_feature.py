"""Tests for the ZScoreFeature rolling z-score implementation."""

from __future__ import annotations

import polars as pl
import pytest

from features.technical.zscore import ZScoreFeature


@pytest.fixture()
def feature() -> ZScoreFeature:
    return ZScoreFeature(window=5)


def _make_df(prices: list[float]) -> pl.DataFrame:
    return pl.DataFrame({"close": prices})


class TestZScoreCompute:
    def test_compute_adds_zscore_column(self, feature: ZScoreFeature) -> None:
        df = _make_df([100.0] * 10)
        result = feature.compute(df)
        assert "zscore" in result.columns

    def test_zscore_zero_at_mean(self, feature: ZScoreFeature) -> None:
        df = _make_df([100.0] * 10)
        result = feature.compute(df)
        non_null = result.filter(pl.col("zscore").is_not_null())
        assert all(v == 0.0 for v in non_null["zscore"].to_list())

    def test_zscore_positive_above_mean(self) -> None:
        feature = ZScoreFeature(window=3)
        prices = [10.0, 10.0, 10.0, 20.0]
        result = feature.compute(_make_df(prices))
        last_zscore = result["zscore"][-1]
        assert last_zscore is not None
        assert last_zscore > 0.0

    def test_zscore_negative_below_mean(self) -> None:
        feature = ZScoreFeature(window=3)
        prices = [20.0, 20.0, 20.0, 10.0]
        result = feature.compute(_make_df(prices))
        last_zscore = result["zscore"][-1]
        assert last_zscore is not None
        assert last_zscore < 0.0

    def test_first_rows_null_during_warmup(self, feature: ZScoreFeature) -> None:
        df = _make_df(list(range(1, 21)))
        result = feature.compute(df)
        warmup = result["zscore"][: feature.lookback_days - 1]
        assert all(v is None for v in warmup.to_list())

    def test_division_by_zero_safe(self, feature: ZScoreFeature) -> None:
        df = _make_df([42.0] * 20)
        result = feature.compute(df)
        non_null = result.filter(pl.col("zscore").is_not_null())
        assert all(v == 0.0 for v in non_null["zscore"].to_list())

    def test_custom_window(self) -> None:
        feature = ZScoreFeature(window=50)
        prices = list(range(1, 101))
        result = feature.compute(_make_df([float(p) for p in prices]))
        assert result["zscore"][48] is None
        assert result["zscore"][49] is not None


class TestZScoreProperties:
    def test_lookback_days_equals_window(self) -> None:
        for w in (5, 20, 50):
            assert ZScoreFeature(window=w).lookback_days == w

    def test_name_includes_window(self) -> None:
        assert ZScoreFeature(window=14).name == "zscore_14"
        assert ZScoreFeature(window=20).name == "zscore_20"

    def test_category_is_technical(self, feature: ZScoreFeature) -> None:
        assert feature.category == "technical"


class TestZScoreValidation:
    def test_validate_insufficient_data(self) -> None:
        feature = ZScoreFeature(window=20)
        df = _make_df([100.0] * 19)
        assert feature.validate(df) is False

    def test_validate_sufficient_data(self) -> None:
        feature = ZScoreFeature(window=20)
        df = _make_df([100.0] * 20)
        assert feature.validate(df) is True
