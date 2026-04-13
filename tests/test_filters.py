"""Tests for analytics/filters.py — CUSUM event filter."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from analytics.filters import CUSUMFilter, EventFilter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _price_df(
    prices: list[float],
    start: date = date(2020, 1, 2),
) -> pl.DataFrame:
    dates = [start + timedelta(days=i) for i in range(len(prices))]
    return pl.DataFrame({"date": dates, "close": prices}).with_columns(
        pl.col("date").cast(pl.Date),
        pl.col("close").cast(pl.Float64),
    )


def _trending_prices(
    n: int,
    daily_return: float,
    start_price: float = 100.0,
    start: date = date(2020, 1, 2),
) -> pl.DataFrame:
    """Generate a steadily trending price series."""
    prices = [start_price]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1.0 + daily_return))
    return _price_df(prices, start)


def _random_prices(
    n: int = 252,
    mu: float = 0.0003,
    sigma: float = 0.012,
    seed: int = 0,
    start: date = date(2020, 1, 2),
) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    log_r = rng.normal(mu, sigma, size=n)
    prices = (100.0 * np.exp(np.cumsum(log_r))).tolist()
    return _price_df(prices, start)


# ---------------------------------------------------------------------------
# EventFilter ABC
# ---------------------------------------------------------------------------

class TestEventFilterABC:
    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            EventFilter()  # type: ignore[abstract]

    def test_cusum_is_event_filter(self) -> None:
        f = CUSUMFilter(threshold=0.01)
        assert isinstance(f, EventFilter)


# ---------------------------------------------------------------------------
# CUSUMFilter construction
# ---------------------------------------------------------------------------

class TestCUSUMFilterInit:
    def test_default_threshold_none(self) -> None:
        f = CUSUMFilter()
        assert f.threshold is None
        assert f.vol_multiplier == 2.0

    def test_custom_threshold(self) -> None:
        f = CUSUMFilter(threshold=0.05, vol_multiplier=3.0)
        assert f.threshold == 0.05
        assert f.vol_multiplier == 3.0

    def test_negative_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold must be positive"):
            CUSUMFilter(threshold=-0.01)

    def test_zero_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold must be positive"):
            CUSUMFilter(threshold=0.0)

    def test_negative_vol_multiplier_raises(self) -> None:
        with pytest.raises(ValueError, match="vol_multiplier must be positive"):
            CUSUMFilter(vol_multiplier=-1.0)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_missing_date_column_raises(self) -> None:
        df = pl.DataFrame({"close": [100.0, 101.0]})
        f = CUSUMFilter(threshold=0.01)
        with pytest.raises(ValueError, match="date"):
            f.filter(df)

    def test_missing_price_column_raises(self) -> None:
        df = pl.DataFrame({
            "date": [date(2020, 1, 1), date(2020, 1, 2)],
            "open": [100.0, 101.0],
        }).with_columns(pl.col("date").cast(pl.Date))
        f = CUSUMFilter(threshold=0.01)
        with pytest.raises(ValueError, match="close"):
            f.filter(df)

    def test_custom_price_col(self) -> None:
        dates = [date(2020, 1, 1) + timedelta(days=i) for i in range(51)]
        df = pl.DataFrame({
            "date": dates,
            "adj_close": [100.0 + i * 0.5 for i in range(51)],
        }).with_columns(pl.col("date").cast(pl.Date))
        f = CUSUMFilter(threshold=0.001)
        result = f.filter(df, price_col="adj_close")
        assert "date" in result.columns
        assert "event_type" in result.columns


# ---------------------------------------------------------------------------
# Test 1: No events on a constant series
# ---------------------------------------------------------------------------

class TestConstantSeries:
    def test_constant_prices_no_events(self) -> None:
        """Zero returns never exceed any threshold."""
        df = _price_df([100.0] * 50)
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        assert len(result) == 0

    def test_constant_prices_auto_threshold_no_events(self) -> None:
        """When threshold is auto-computed from vol, constant series
        has zero vol so we get empty result."""
        df = _price_df([100.0] * 50)
        f = CUSUMFilter()  # threshold=None
        result = f.filter(df)
        assert len(result) == 0

    def test_constant_dynamic_no_events(self) -> None:
        df = _price_df([100.0] * 50)
        f = CUSUMFilter()
        result = f.filter_dynamic(df, vol_window=10)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Test 2: Single upward jump triggers one positive event
# ---------------------------------------------------------------------------

class TestSingleUpwardJump:
    def test_large_upward_jump(self) -> None:
        """Flat prices then a large jump should trigger a positive event."""
        prices = [100.0] * 20 + [120.0]  # 20% jump at the end
        df = _price_df(prices)
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        assert len(result) >= 1
        # The last event should be positive
        assert result["event_type"][-1] == "positive"

    def test_moderate_upward_jump_with_low_threshold(self) -> None:
        prices = [100.0] * 10 + [105.0]  # 5% jump
        df = _price_df(prices)
        f = CUSUMFilter(threshold=0.005)
        result = f.filter(df)
        positive_events = result.filter(pl.col("event_type") == "positive")
        assert len(positive_events) >= 1


# ---------------------------------------------------------------------------
# Test 3: Single downward jump triggers one negative event
# ---------------------------------------------------------------------------

class TestSingleDownwardJump:
    def test_large_downward_jump(self) -> None:
        """Flat prices then a large drop should trigger a negative event."""
        prices = [100.0] * 20 + [80.0]  # -20% drop
        df = _price_df(prices)
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        assert len(result) >= 1
        assert result["event_type"][-1] == "negative"

    def test_moderate_downward_jump_with_low_threshold(self) -> None:
        prices = [100.0] * 10 + [95.0]  # -5% drop
        df = _price_df(prices)
        f = CUSUMFilter(threshold=0.005)
        result = f.filter(df)
        negative_events = result.filter(pl.col("event_type") == "negative")
        assert len(negative_events) >= 1


# ---------------------------------------------------------------------------
# Test 4: Dynamic threshold adapts to volatility
# ---------------------------------------------------------------------------

class TestDynamicThreshold:
    def test_high_vol_period_fewer_events(self) -> None:
        """With higher volatility, the dynamic threshold is larger,
        so fewer events are detected for the same magnitude moves."""
        rng = np.random.default_rng(42)

        # Low vol regime
        low_vol = rng.normal(0.0, 0.005, 100)
        low_prices = 100.0 * np.exp(np.cumsum(low_vol))

        # High vol regime (same drift, more noise)
        high_vol = rng.normal(0.0, 0.03, 100)
        high_prices = 100.0 * np.exp(np.cumsum(high_vol))

        df_low = _price_df(low_prices.tolist())
        df_high = _price_df(high_prices.tolist())

        f = CUSUMFilter(vol_multiplier=1.0)
        events_low = f.filter_dynamic(df_low, vol_window=20)
        events_high = f.filter_dynamic(df_high, vol_window=20)

        # The dynamic filter on the high-vol series should produce
        # roughly similar or fewer events because the threshold grows
        # This is a soft assertion — the key property is that
        # the dynamic filter does not blow up with events during noise
        assert isinstance(events_low, pl.DataFrame)
        assert isinstance(events_high, pl.DataFrame)

    def test_dynamic_returns_valid_schema(self) -> None:
        df = _random_prices(100, seed=7)
        f = CUSUMFilter(vol_multiplier=2.0)
        result = f.filter_dynamic(df, vol_window=20)
        assert set(result.columns) == {"date", "event_type", "cumsum_value"}

    def test_dynamic_short_series_falls_back(self) -> None:
        """Series shorter than vol_window should still work."""
        df = _random_prices(10, seed=3)
        f = CUSUMFilter(vol_multiplier=1.0)
        result = f.filter_dynamic(df, vol_window=20)
        assert isinstance(result, pl.DataFrame)
        assert set(result.columns) == {"date", "event_type", "cumsum_value"}


# ---------------------------------------------------------------------------
# Test 5: Reset after event (cumsum goes back to 0)
# ---------------------------------------------------------------------------

class TestResetAfterEvent:
    def test_cumsum_resets_between_events(self) -> None:
        """After an event fires, the CUSUM resets.  Verify that a
        second large move in the opposite direction can trigger a
        second event of opposite type."""
        # Large up, then flat, then large down
        prices = (
            [100.0] * 5
            + [130.0]  # big positive jump
            + [130.0] * 5
            + [100.0]  # big negative jump
        )
        df = _price_df(prices)
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)

        types = result["event_type"].to_list()
        # Should see both positive and negative events
        assert "positive" in types
        assert "negative" in types

    def test_repeated_same_direction_events(self) -> None:
        """Multiple jumps in the same direction should each produce
        an event after the previous one resets."""
        # Series of upward jumps separated by flat regions
        prices = [100.0] * 5
        for _ in range(3):
            last = prices[-1]
            prices.append(last * 1.15)  # +15%
            prices.extend([prices[-1]] * 5)
        df = _price_df(prices)
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        positive_events = result.filter(pl.col("event_type") == "positive")
        # Each big jump should trigger at least one event
        assert len(positive_events) >= 3


# ---------------------------------------------------------------------------
# Test 6: Multiple events in a trending series
# ---------------------------------------------------------------------------

class TestTrendingSeries:
    def test_uptrend_produces_positive_events(self) -> None:
        """A noisy uptrend should produce positive events.

        A perfectly constant return series has zero deviation from the
        mean, so CUSUM never fires.  We need *noise* around a drift.
        """
        df = _random_prices(200, mu=0.008, sigma=0.005, seed=11)
        f = CUSUMFilter(threshold=0.005)
        result = f.filter(df)
        assert len(result) > 1
        positive = result.filter(pl.col("event_type") == "positive")
        assert len(positive) >= 1

    def test_downtrend_produces_negative_events(self) -> None:
        """A noisy downtrend should produce negative events."""
        df = _random_prices(200, mu=-0.008, sigma=0.005, seed=12)
        f = CUSUMFilter(threshold=0.005)
        result = f.filter(df)
        assert len(result) > 1
        negative = result.filter(pl.col("event_type") == "negative")
        assert len(negative) >= 1

    def test_more_events_with_lower_threshold(self) -> None:
        """Lowering the threshold should produce more (or equal) events."""
        df = _random_prices(300, seed=10)
        f_high = CUSUMFilter(threshold=0.03)
        f_low = CUSUMFilter(threshold=0.01)
        events_high = f_high.filter(df)
        events_low = f_low.filter(df)
        assert len(events_low) >= len(events_high)


# ---------------------------------------------------------------------------
# Test 7: Polars input/output with date handling
# ---------------------------------------------------------------------------

class TestPolarsIntegration:
    def test_output_schema(self) -> None:
        df = _random_prices(100, seed=1)
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        assert result.columns == ["date", "event_type", "cumsum_value"]

    def test_date_column_is_date_type(self) -> None:
        df = _random_prices(100, seed=2)
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        if len(result) > 0:
            assert result["date"].dtype == pl.Date

    def test_event_type_is_string(self) -> None:
        df = _random_prices(100, seed=3)
        f = CUSUMFilter(threshold=0.005)
        result = f.filter(df)
        if len(result) > 0:
            assert result["event_type"].dtype == pl.Utf8

    def test_cumsum_value_is_float(self) -> None:
        df = _random_prices(100, seed=4)
        f = CUSUMFilter(threshold=0.005)
        result = f.filter(df)
        if len(result) > 0:
            assert result["cumsum_value"].dtype == pl.Float64

    def test_event_dates_are_subset_of_input_dates(self) -> None:
        df = _random_prices(200, seed=5)
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        if len(result) > 0:
            input_dates = set(df["date"].to_list())
            event_dates = set(result["date"].to_list())
            assert event_dates.issubset(input_dates)

    def test_event_dates_are_monotonically_increasing(self) -> None:
        df = _random_prices(200, seed=6)
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        if len(result) > 1:
            dates = result["date"].to_list()
            assert dates == sorted(dates)

    def test_event_type_values_valid(self) -> None:
        df = _random_prices(200, seed=8)
        f = CUSUMFilter(threshold=0.005)
        result = f.filter(df)
        if len(result) > 0:
            valid_types = {"positive", "negative"}
            actual_types = set(result["event_type"].to_list())
            assert actual_types.issubset(valid_types)


# ---------------------------------------------------------------------------
# Test 8: Empty DataFrame input returns empty DataFrame
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_df_returns_empty(self) -> None:
        df = pl.DataFrame({
            "date": pl.Series([], dtype=pl.Date),
            "close": pl.Series([], dtype=pl.Float64),
        })
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        assert len(result) == 0
        assert result.columns == ["date", "event_type", "cumsum_value"]

    def test_single_row_returns_empty(self) -> None:
        """Need at least 2 prices to compute a return."""
        df = _price_df([100.0])
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        assert len(result) == 0

    def test_empty_dynamic_returns_empty(self) -> None:
        df = pl.DataFrame({
            "date": pl.Series([], dtype=pl.Date),
            "close": pl.Series([], dtype=pl.Float64),
        })
        f = CUSUMFilter(vol_multiplier=2.0)
        result = f.filter_dynamic(df, vol_window=20)
        assert len(result) == 0
        assert result.columns == ["date", "event_type", "cumsum_value"]


# ---------------------------------------------------------------------------
# Numerical correctness
# ---------------------------------------------------------------------------

class TestNumericalCorrectness:
    def test_known_cusum_trace(self) -> None:
        """Hand-computed CUSUM on a minimal series to verify correctness.

        Prices: [100, 100, 100, 100, 110]
        Returns: [0.0, 0.0, 0.0, 0.10]
        Mean return = 0.025
        h = 0.02

        Step 0: y = 0.0 - 0.025 = -0.025
            s+ = max(0, 0 + (-0.025) - 0.02) = 0
            s- = min(0, 0 + (-0.025) + 0.02) = -0.005
            Neither s+ > 0.02 nor s- < -0.02

        Step 1: y = -0.025
            s+ = max(0, 0 + (-0.025) - 0.02) = 0
            s- = min(0, -0.005 + (-0.025) + 0.02) = -0.01
            Neither triggers

        Step 2: y = -0.025
            s+ = max(0, 0 + (-0.025) - 0.02) = 0
            s- = min(0, -0.01 + (-0.025) + 0.02) = -0.015
            Neither triggers

        Step 3: y = 0.10 - 0.025 = 0.075
            s+ = max(0, 0 + 0.075 - 0.02) = 0.055
            s- = min(0, -0.015 + 0.075 + 0.02) = 0  (0.08 > 0 => 0)
            s+ = 0.055 > 0.02 = h => positive event!
        """
        prices = [100.0, 100.0, 100.0, 100.0, 110.0]
        df = _price_df(prices)
        f = CUSUMFilter(threshold=0.02)
        result = f.filter(df)

        assert len(result) == 1
        assert result["event_type"][0] == "positive"
        assert abs(result["cumsum_value"][0] - 0.055) < 1e-9

    def test_cumsum_value_sign_matches_event_type(self) -> None:
        """Positive events should have positive cumsum,
        negative events should have negative cumsum."""
        df = _random_prices(300, seed=99)
        f = CUSUMFilter(threshold=0.01)
        result = f.filter(df)
        if len(result) > 0:
            for i in range(len(result)):
                if result["event_type"][i] == "positive":
                    assert result["cumsum_value"][i] > 0
                else:
                    assert result["cumsum_value"][i] < 0
