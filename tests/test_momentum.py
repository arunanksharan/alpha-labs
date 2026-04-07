"""Tests for the MomentumFeature and MomentumStrategy."""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl
import pytest

from core.features import FeatureRegistry
from core.strategies import StrategyRegistry
from features.technical.momentum import MomentumFeature
from strategies.momentum.strategy import MomentumStrategy


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


def _make_single_ticker_df(
    prices: list[float],
    ticker: str = "AAPL",
    start: date = date(2022, 1, 3),
) -> pl.DataFrame:
    """Build a single-ticker OHLCV-like DataFrame with known close prices."""
    n = len(prices)
    dates = _business_dates(start, n)
    return pl.DataFrame({
        "date": dates,
        "ticker": [ticker] * n,
        "close": prices,
    }).with_columns(pl.col("date").cast(pl.Date))


def _make_multi_ticker_features(
    momentum_values: dict[str, float],
    date_val: date = date(2023, 6, 1),
) -> pl.DataFrame:
    """Build a features DataFrame with pre-set momentum values per ticker."""
    rows = [
        {"date": date_val, "ticker": t, "momentum": m}
        for t, m in momentum_values.items()
    ]
    return pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def feature() -> MomentumFeature:
    return MomentumFeature(lookback=10, skip_recent=2)


@pytest.fixture()
def strategy() -> MomentumStrategy:
    return MomentumStrategy(
        lookback=252,
        skip_recent=21,
        top_pct=0.2,
        bottom_pct=0.2,
    )


# ---------------------------------------------------------------------------
# Feature tests
# ---------------------------------------------------------------------------


class TestMomentumFeatureCompute:
    def test_momentum_feature_adds_column(self, feature: MomentumFeature) -> None:
        prices = [100.0] * 20
        df = _make_single_ticker_df(prices)
        result = feature.compute(df)
        assert "momentum" in result.columns

    def test_momentum_formula_known_values(self) -> None:
        """Price doubles over lookback period -> momentum = 1.0."""
        feat = MomentumFeature(lookback=5, skip_recent=0)
        # Build prices: starts at 50, then at index 5 the price is 100.
        # With skip_recent=0: momentum[5] = price[5] / price[0] - 1 = 100/50 - 1 = 1.0
        prices = [50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        df = _make_single_ticker_df(prices)
        result = feat.compute(df)
        mom = result["momentum"].to_list()
        # First 5 rows should be null (need lookback=5 shift).
        assert mom[5] == pytest.approx(1.0)

    def test_skip_recent_works(self) -> None:
        """Verify skip_recent ignores the most recent days."""
        feat = MomentumFeature(lookback=5, skip_recent=2)
        # 8 prices: index 0..7
        # momentum[7] = price[7-2] / price[7-5] - 1 = price[5] / price[2] - 1
        prices = [100.0, 100.0, 50.0, 60.0, 70.0, 200.0, 80.0, 90.0]
        df = _make_single_ticker_df(prices)
        result = feat.compute(df)
        mom = result["momentum"].to_list()
        # At index 7: shift(2) -> price[5]=200, shift(5) -> price[2]=50
        # momentum = 200/50 - 1 = 3.0
        assert mom[7] == pytest.approx(3.0)

    def test_warmup_nulls(self) -> None:
        """First `lookback` rows should have null momentum."""
        feat = MomentumFeature(lookback=10, skip_recent=2)
        prices = [100.0 + i for i in range(20)]
        df = _make_single_ticker_df(prices)
        result = feat.compute(df)
        mom = result["momentum"].to_list()
        # shift(lookback) produces nulls for first `lookback` rows.
        for i in range(10):
            assert mom[i] is None, f"Expected null at index {i}, got {mom[i]}"
        # After warmup, values should be non-null.
        assert mom[10] is not None


class TestMomentumFeatureProperties:
    def test_momentum_feature_properties(self) -> None:
        feat = MomentumFeature(lookback=252, skip_recent=21)
        assert feat.name == "momentum_252_21"
        assert feat.lookback_days == 252
        assert feat.category == "technical"

    def test_name_varies_with_params(self) -> None:
        assert MomentumFeature(lookback=126, skip_recent=5).name == "momentum_126_5"
        assert MomentumFeature(lookback=60, skip_recent=0).name == "momentum_60_0"


# ---------------------------------------------------------------------------
# Strategy tests
# ---------------------------------------------------------------------------


class TestMomentumStrategyProperties:
    def test_strategy_name(self) -> None:
        s = MomentumStrategy()
        assert s.name == "momentum"

    def test_required_features(self) -> None:
        s = MomentumStrategy(lookback=252, skip_recent=21)
        assert s.required_features == ["momentum_252_21"]


class TestMomentumStrategySignals:
    def test_strategy_long_top_short_bottom(self) -> None:
        """With 5 tickers and 20% buckets, top 1 is long, bottom 1 is short."""
        strategy = MomentumStrategy(top_pct=0.2, bottom_pct=0.2)
        features = _make_multi_ticker_features({
            "A": -0.20,  # lowest — should be short
            "B": -0.05,
            "C": 0.00,
            "D": 0.10,
            "E": 0.30,  # highest — should be long
        })
        signals = strategy.generate_signals(features)

        long_tickers = {s.ticker for s in signals if s.direction > 0}
        short_tickers = {s.ticker for s in signals if s.direction < 0}

        assert "E" in long_tickers
        assert "A" in short_tickers

    def test_strategy_no_signal_for_middle(self) -> None:
        """Middle tickers should not produce signals."""
        strategy = MomentumStrategy(top_pct=0.2, bottom_pct=0.2)
        features = _make_multi_ticker_features({
            "A": -0.20,
            "B": -0.05,
            "C": 0.00,
            "D": 0.10,
            "E": 0.30,
        })
        signals = strategy.generate_signals(features)
        signal_tickers = {s.ticker for s in signals}

        # B, C, D are in the middle — no signals.
        assert "B" not in signal_tickers
        assert "C" not in signal_tickers
        assert "D" not in signal_tickers

    def test_strategy_signal_bounds(self) -> None:
        """Direction should be -1 or 1; confidence between 0 and 1."""
        strategy = MomentumStrategy(top_pct=0.2, bottom_pct=0.2)
        features = _make_multi_ticker_features({
            "A": -0.50,
            "B": -0.10,
            "C": 0.05,
            "D": 0.15,
            "E": 0.40,
        })
        signals = strategy.generate_signals(features)

        for sig in signals:
            assert sig.direction in (-1.0, 1.0)
            assert 0.0 <= sig.confidence <= 1.0

    def test_larger_universe(self) -> None:
        """10 tickers with 20% buckets: 2 long, 2 short, 6 neutral."""
        strategy = MomentumStrategy(top_pct=0.2, bottom_pct=0.2)
        features = _make_multi_ticker_features({
            f"T{i:02d}": float(i) / 10.0 for i in range(10)
        })
        signals = strategy.generate_signals(features)

        longs = [s for s in signals if s.direction > 0]
        shorts = [s for s in signals if s.direction < 0]

        assert len(longs) == 2
        assert len(shorts) == 2


class TestMomentumStrategyPositions:
    def test_get_positions_equal_weight(self) -> None:
        """Positions should be equal-weight within each leg."""
        strategy = MomentumStrategy(top_pct=0.2, bottom_pct=0.2)
        features = _make_multi_ticker_features({
            f"T{i:02d}": float(i) / 10.0 for i in range(10)
        })
        signals = strategy.generate_signals(features)
        positions = strategy.get_positions(signals, capital=100_000.0)

        assert "ticker" in positions.columns
        assert "weight" in positions.columns
        assert "target_value" in positions.columns

        long_pos = positions.filter(pl.col("weight") > 0)
        short_pos = positions.filter(pl.col("weight") < 0)

        # Equal weight within longs.
        long_weights = long_pos["weight"].to_list()
        assert len(set(long_weights)) == 1

        # Equal weight within shorts.
        short_weights = short_pos["weight"].abs().to_list()
        assert len(set(short_weights)) == 1

    def test_get_positions_empty_signals(self) -> None:
        strategy = MomentumStrategy()
        positions = strategy.get_positions([], capital=100_000.0)
        assert len(positions) == 0
        assert set(positions.columns) == {"ticker", "weight", "target_shares", "target_value"}


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestRegistryRegistration:
    def test_feature_registry(self) -> None:
        FeatureRegistry.register(MomentumFeature)
        assert "momentum_252_21" in FeatureRegistry.list_features()
        feat = FeatureRegistry.get("momentum_252_21")
        assert isinstance(feat, MomentumFeature)

    def test_strategy_registry(self) -> None:
        StrategyRegistry.register(MomentumStrategy)
        assert "momentum" in StrategyRegistry.list_strategies()
        strat = StrategyRegistry.get("momentum")
        assert isinstance(strat, MomentumStrategy)

    def test_feature_in_technical_category(self) -> None:
        FeatureRegistry.register(MomentumFeature)
        technical = FeatureRegistry.list_features(category="technical")
        assert "momentum_252_21" in technical
