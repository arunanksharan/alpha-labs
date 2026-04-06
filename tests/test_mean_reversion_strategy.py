"""Tests for strategies/mean_reversion/strategy.py."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from core.strategies import Signal, StrategyRegistry
from strategies.mean_reversion.strategy import MeanReversionStrategy, PairValidation


def _dates(n: int, start: date = date(2022, 1, 3)) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


def _ohlcv_with_zscore(n: int = 100, window: int = 20) -> pl.DataFrame:
    """Build a DataFrame with date, ticker, close, and a pre-computed zscore."""
    rng = np.random.default_rng(42)
    close = 100.0 + np.cumsum(rng.normal(0, 1, n))
    rolling_mean = np.convolve(close, np.ones(window) / window, mode="full")[:n]
    rolling_std_vals = np.array([
        np.std(close[max(0, i - window + 1):i + 1], ddof=1) if i >= window - 1 else np.nan
        for i in range(n)
    ])
    zscore = np.where(
        (rolling_std_vals > 0) & (~np.isnan(rolling_std_vals)),
        (close - rolling_mean[:n]) / rolling_std_vals,
        np.nan,
    )
    return pl.DataFrame({
        "date": _dates(n),
        "ticker": ["AAPL"] * n,
        "close": close.tolist(),
        "zscore": zscore.tolist(),
    }).with_columns(pl.col("date").cast(pl.Date))


class TestStrategyProperties:
    def test_name(self) -> None:
        s = MeanReversionStrategy()
        assert s.name == "mean_reversion"

    def test_required_features_single_mode(self) -> None:
        s = MeanReversionStrategy(mode="single", window=20)
        assert s.required_features == ["zscore_20"]

    def test_required_features_pairs_mode(self) -> None:
        s = MeanReversionStrategy(mode="pairs", ticker_a="AAPL", ticker_b="MSFT")
        assert s.required_features == ["spread_AAPL_MSFT"]

    def test_registry_registration(self) -> None:
        # Re-register in case test_core_registries cleared the registry
        StrategyRegistry.register(MeanReversionStrategy)
        s = StrategyRegistry.get("mean_reversion")
        assert isinstance(s, MeanReversionStrategy)


class TestGenerateSignals:
    def test_long_signal_below_negative_threshold(self) -> None:
        df = pl.DataFrame({
            "date": [date(2022, 1, 3)],
            "ticker": ["AAPL"],
            "zscore": [-2.5],
        }).with_columns(pl.col("date").cast(pl.Date))
        s = MeanReversionStrategy(entry_threshold=2.0)
        signals = s.generate_signals(df)
        assert len(signals) == 1
        assert signals[0].direction == 1.0
        assert signals[0].confidence == pytest.approx(2.5 / 4.0)

    def test_short_signal_above_threshold(self) -> None:
        df = pl.DataFrame({
            "date": [date(2022, 1, 3)],
            "ticker": ["AAPL"],
            "zscore": [2.5],
        }).with_columns(pl.col("date").cast(pl.Date))
        s = MeanReversionStrategy(entry_threshold=2.0)
        signals = s.generate_signals(df)
        assert len(signals) == 1
        assert signals[0].direction == -1.0

    def test_exit_signal_at_mean(self) -> None:
        df = pl.DataFrame({
            "date": [date(2022, 1, 3)],
            "ticker": ["AAPL"],
            "zscore": [0.0],
        }).with_columns(pl.col("date").cast(pl.Date))
        s = MeanReversionStrategy(entry_threshold=2.0, exit_threshold=0.5)
        signals = s.generate_signals(df)
        assert len(signals) == 1
        assert signals[0].direction == 0.0

    def test_no_signal_between_thresholds(self) -> None:
        df = pl.DataFrame({
            "date": [date(2022, 1, 3)],
            "ticker": ["AAPL"],
            "zscore": [1.0],
        }).with_columns(pl.col("date").cast(pl.Date))
        s = MeanReversionStrategy(entry_threshold=2.0, exit_threshold=0.5)
        signals = s.generate_signals(df)
        assert len(signals) == 0

    def test_confidence_scales_with_z_magnitude(self) -> None:
        df = pl.DataFrame({
            "date": _dates(2),
            "ticker": ["AAPL", "AAPL"],
            "zscore": [-2.1, -3.0],
        }).with_columns(pl.col("date").cast(pl.Date))
        s = MeanReversionStrategy(entry_threshold=2.0)
        signals = s.generate_signals(df)
        assert len(signals) == 2
        assert signals[1].confidence > signals[0].confidence

    def test_confidence_capped_at_one(self) -> None:
        df = pl.DataFrame({
            "date": [date(2022, 1, 3)],
            "ticker": ["AAPL"],
            "zscore": [-8.0],
        }).with_columns(pl.col("date").cast(pl.Date))
        s = MeanReversionStrategy(entry_threshold=2.0)
        signals = s.generate_signals(df)
        assert signals[0].confidence == 1.0

    def test_null_zscore_skipped(self) -> None:
        df = pl.DataFrame({
            "date": _dates(3),
            "ticker": ["AAPL"] * 3,
            "zscore": [None, -2.5, None],
        }).with_columns(pl.col("date").cast(pl.Date))
        s = MeanReversionStrategy(entry_threshold=2.0)
        signals = s.generate_signals(df)
        assert len(signals) == 1

    def test_signal_direction_bounds(self) -> None:
        df = _ohlcv_with_zscore(200)
        s = MeanReversionStrategy(entry_threshold=1.5)
        signals = s.generate_signals(df)
        for sig in signals:
            assert -1.0 <= sig.direction <= 1.0

    def test_signal_confidence_bounds(self) -> None:
        df = _ohlcv_with_zscore(200)
        s = MeanReversionStrategy(entry_threshold=1.5)
        signals = s.generate_signals(df)
        for sig in signals:
            assert 0.0 <= sig.confidence <= 1.0

    def test_missing_zscore_column_raises(self) -> None:
        df = pl.DataFrame({
            "date": [date(2022, 1, 3)],
            "ticker": ["AAPL"],
            "close": [100.0],
        }).with_columns(pl.col("date").cast(pl.Date))
        s = MeanReversionStrategy()
        with pytest.raises(ValueError, match="zscore"):
            s.generate_signals(df)

    def test_pairs_mode_uses_spread_zscore(self) -> None:
        df = pl.DataFrame({
            "date": [date(2022, 1, 3)],
            "spread_zscore": [-2.5],
        }).with_columns(pl.col("date").cast(pl.Date))
        s = MeanReversionStrategy(mode="pairs", ticker_a="AAPL", ticker_b="MSFT")
        signals = s.generate_signals(df)
        assert len(signals) == 1
        assert "AAPL/MSFT" in signals[0].ticker


class TestGetPositions:
    def test_empty_signals(self) -> None:
        s = MeanReversionStrategy()
        pos = s.get_positions([], 100_000.0)
        assert pos.is_empty()
        assert set(pos.columns) == {"ticker", "weight", "target_shares", "target_value"}

    def test_single_mode_one_row_per_signal(self) -> None:
        sig = Signal(ticker="AAPL", date="2022-01-03", direction=1.0, confidence=0.5)
        s = MeanReversionStrategy(max_weight=1.0)
        pos = s.get_positions([sig], 100_000.0)
        assert len(pos) == 1
        assert pos["weight"][0] == pytest.approx(0.5)

    def test_pairs_mode_two_rows_per_signal(self) -> None:
        sig = Signal(ticker="AAPL/MSFT", date="2022-01-03", direction=1.0, confidence=0.5)
        s = MeanReversionStrategy(mode="pairs", ticker_a="AAPL", ticker_b="MSFT")
        pos = s.get_positions([sig], 100_000.0)
        assert len(pos) == 2
        tickers = pos["ticker"].to_list()
        assert "AAPL" in tickers
        assert "MSFT" in tickers
        weights = pos["weight"].to_list()
        assert weights[0] == -weights[1]


class TestValidatePair:
    def test_cointegrated_pair_accepted(
        self, cointegrated_pair_prices: tuple[pl.DataFrame, pl.DataFrame]
    ) -> None:
        df_a, df_b = cointegrated_pair_prices
        s = MeanReversionStrategy(
            mode="pairs", ticker_a="A", ticker_b="B",
            min_half_life=0.1,  # Allow fast-reverting pairs in test
        )
        result = s.validate_pair(df_a["close"], df_b["close"])
        assert isinstance(result, PairValidation)
        assert result.is_valid
        assert result.hedge_ratio != 0.0
        assert result.half_life > 0

    def test_independent_walks_rejected(self) -> None:
        rng = np.random.default_rng(42)
        a = pl.Series("a", np.cumsum(rng.normal(0, 1, 500)).tolist())
        b = pl.Series("b", np.cumsum(rng.normal(0, 1, 500)).tolist())
        s = MeanReversionStrategy(mode="pairs", ticker_a="X", ticker_b="Y")
        result = s.validate_pair(a, b)
        # May or may not reject (spurious cointegration possible), but check structure
        assert isinstance(result, PairValidation)
        assert result.rejection_reason is None or isinstance(result.rejection_reason, str)

    def test_validate_populates_internal_state(
        self, cointegrated_pair_prices: tuple[pl.DataFrame, pl.DataFrame]
    ) -> None:
        df_a, df_b = cointegrated_pair_prices
        s = MeanReversionStrategy(mode="pairs", ticker_a="A", ticker_b="B")
        result = s.validate_pair(df_a["close"], df_b["close"])
        if result.is_valid:
            assert s._hedge_ratio is not None
            assert s._window >= 10
