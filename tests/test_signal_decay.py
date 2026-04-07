"""Tests for SignalDecayAnalyzer."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from analytics.signal_decay import SignalDecayAnalyzer


# ---------------------------------------------------------------------------
# Fixtures -- synthetic data
# ---------------------------------------------------------------------------

def _business_dates(start: date, n: int) -> list[date]:
    """Generate *n* business days starting from *start*."""
    dates: list[date] = []
    current = start
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


@pytest.fixture()
def price_data() -> pl.DataFrame:
    """Synthetic price panel: 5 tickers, 200 business days."""
    rng = np.random.default_rng(42)
    n_days = 200
    tickers = [f"T{i}" for i in range(5)]
    dates = _business_dates(date(2024, 1, 2), n_days)

    rows: list[dict[str, object]] = []
    for tk in tickers:
        # Random walk prices starting at 100
        log_returns = rng.normal(0.0003, 0.015, size=n_days)
        prices = 100.0 * np.exp(np.cumsum(log_returns))
        for d, p in zip(dates, prices, strict=True):
            rows.append({"date": d, "ticker": tk, "close": float(p)})

    return pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))


@pytest.fixture()
def perfect_signal(price_data: pl.DataFrame) -> pl.DataFrame:
    """Signal that perfectly predicts 1-day forward returns.

    signal_value = sign(close[t+1] / close[t] - 1) for each ticker.
    """
    rows: list[dict[str, object]] = []
    for tk in price_data["ticker"].unique().to_list():
        tk_data = price_data.filter(pl.col("ticker") == tk).sort("date")
        closes = tk_data["close"].to_numpy()
        dates = tk_data["date"].to_list()
        for i in range(len(closes) - 1):
            fwd_ret = closes[i + 1] / closes[i] - 1.0
            rows.append(
                {
                    "date": dates[i],
                    "ticker": tk,
                    "signal_value": float(np.sign(fwd_ret)),
                }
            )
    return pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))


@pytest.fixture()
def random_signal(price_data: pl.DataFrame) -> pl.DataFrame:
    """Random noise signal -- should have IC near zero."""
    rng = np.random.default_rng(99)
    rows: list[dict[str, object]] = []
    for tk in price_data["ticker"].unique().to_list():
        tk_data = price_data.filter(pl.col("ticker") == tk).sort("date")
        dates = tk_data["date"].to_list()
        for d in dates[:-1]:
            rows.append(
                {
                    "date": d,
                    "ticker": tk,
                    "signal_value": float(rng.standard_normal()),
                }
            )
    return pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))


@pytest.fixture()
def analyzer() -> SignalDecayAnalyzer:
    return SignalDecayAnalyzer(max_horizon=30)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestICCurve:
    def test_ic_curve_shape(
        self,
        analyzer: SignalDecayAnalyzer,
        perfect_signal: pl.DataFrame,
        price_data: pl.DataFrame,
    ) -> None:
        curve = analyzer.compute_ic_curve(perfect_signal, price_data)
        assert len(curve) == analyzer.max_horizon

    def test_ic_curve_columns(
        self,
        analyzer: SignalDecayAnalyzer,
        perfect_signal: pl.DataFrame,
        price_data: pl.DataFrame,
    ) -> None:
        curve = analyzer.compute_ic_curve(perfect_signal, price_data)
        expected_cols = {"horizon", "ic", "ic_std", "ic_tstat", "is_significant"}
        assert set(curve.columns) == expected_cols

    def test_perfect_signal_high_ic(
        self,
        analyzer: SignalDecayAnalyzer,
        perfect_signal: pl.DataFrame,
        price_data: pl.DataFrame,
    ) -> None:
        curve = analyzer.compute_ic_curve(perfect_signal, price_data)
        ic_at_1 = float(curve.filter(pl.col("horizon") == 1)["ic"][0])
        # A perfect 1-day signal should have high IC at horizon 1
        assert ic_at_1 > 0.3, f"Expected high IC at horizon 1, got {ic_at_1}"

    def test_random_signal_near_zero_ic(
        self,
        analyzer: SignalDecayAnalyzer,
        random_signal: pl.DataFrame,
        price_data: pl.DataFrame,
    ) -> None:
        curve = analyzer.compute_ic_curve(random_signal, price_data)
        # Average absolute IC across all horizons should be small
        mean_abs_ic = float(curve["ic"].abs().mean())
        assert mean_abs_ic < 0.15, f"Random signal IC too high: {mean_abs_ic}"


class TestHalfLife:
    def test_ic_half_life_positive(
        self,
        analyzer: SignalDecayAnalyzer,
        perfect_signal: pl.DataFrame,
        price_data: pl.DataFrame,
    ) -> None:
        curve = analyzer.compute_ic_curve(perfect_signal, price_data)
        half_life = analyzer.compute_ic_half_life(curve)
        assert half_life > 0, f"Half-life should be positive, got {half_life}"
        assert np.isfinite(half_life), "Half-life should be finite for a decaying signal"


class TestRollingIC:
    def test_rolling_ic_shape(
        self,
        analyzer: SignalDecayAnalyzer,
        perfect_signal: pl.DataFrame,
        price_data: pl.DataFrame,
    ) -> None:
        result = analyzer.rolling_ic(
            perfect_signal, price_data, horizon=5, window=30
        )
        assert len(result) > 0
        assert set(result.columns) == {"date", "ic", "is_significant"}


class TestCompareDecay:
    def test_compare_decay_multiple_signals(
        self,
        analyzer: SignalDecayAnalyzer,
        perfect_signal: pl.DataFrame,
        random_signal: pl.DataFrame,
        price_data: pl.DataFrame,
    ) -> None:
        result = analyzer.compare_decay(
            {"perfect": perfect_signal, "random": random_signal},
            price_data,
        )
        assert "signal_name" in result.columns
        assert "horizon" in result.columns
        assert "ic" in result.columns
        names = result["signal_name"].unique().to_list()
        assert set(names) == {"perfect", "random"}
        # Should have max_horizon rows per signal
        assert len(result) == 2 * analyzer.max_horizon


class TestDecaySummary:
    def test_decay_summary_keys(
        self,
        analyzer: SignalDecayAnalyzer,
        perfect_signal: pl.DataFrame,
        price_data: pl.DataFrame,
    ) -> None:
        curve = analyzer.compute_ic_curve(perfect_signal, price_data)
        summary = analyzer.decay_summary(curve)
        expected_keys = {
            "ic_at_1d",
            "ic_at_5d",
            "ic_at_20d",
            "half_life",
            "max_ic",
            "max_ic_horizon",
        }
        assert set(summary.keys()) == expected_keys
        for v in summary.values():
            assert isinstance(v, float)
