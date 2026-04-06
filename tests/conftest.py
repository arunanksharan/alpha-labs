"""Shared pytest fixtures for the quant research platform test suite."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from data.storage.store import DataStore


def _business_dates(start: date, n: int) -> list[date]:
    dates: list[date] = []
    current = start
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


@pytest.fixture(scope="session")
def sample_ohlcv_data() -> pl.DataFrame:
    rng = np.random.default_rng(42)
    n = 500
    start = date(2022, 1, 3)
    dates = _business_dates(start, n)

    log_returns = rng.normal(0.0003, 0.012, size=n)
    close = 100.0 * np.exp(np.cumsum(log_returns))
    noise = rng.uniform(0.001, 0.015, size=n)

    high = close * (1.0 + noise)
    low = close * (1.0 - noise)
    open_ = low + rng.uniform(0.0, 1.0, size=n) * (high - low)
    volume = rng.integers(500_000, 5_000_000, size=n).astype(np.float64)

    return pl.DataFrame(
        {
            "date": dates,
            "open": open_.tolist(),
            "high": high.tolist(),
            "low": low.tolist(),
            "close": close.tolist(),
            "volume": volume.tolist(),
        }
    ).with_columns(pl.col("date").cast(pl.Date))


@pytest.fixture(scope="session")
def sample_returns_data() -> pl.DataFrame:
    rng = np.random.default_rng(7)
    n = 500
    start = date(2022, 1, 3)
    dates = _business_dates(start, n)

    r_a = rng.normal(0.0004, 0.011, size=n)
    r_b = 0.6 * r_a + 0.4 * rng.normal(0.0002, 0.009, size=n)
    r_c = rng.normal(0.0001, 0.014, size=n)

    return pl.DataFrame(
        {
            "date": dates,
            "returns_a": r_a.tolist(),
            "returns_b": r_b.tolist(),
            "returns_c": r_c.tolist(),
        }
    ).with_columns(pl.col("date").cast(pl.Date))


@pytest.fixture(scope="session")
def sample_macro_data() -> pl.DataFrame:
    rng = np.random.default_rng(99)
    n = 120
    start = date(2014, 1, 1)
    dates = [start + timedelta(days=30 * i) for i in range(n)]

    gdp_growth = rng.normal(0.005, 0.002, size=n).tolist()
    cpi = (np.cumsum(rng.normal(0.002, 0.001, size=n)) + 2.0).tolist()

    return pl.DataFrame(
        {
            "date": dates,
            "gdp_growth": gdp_growth,
            "cpi": cpi,
        }
    ).with_columns(pl.col("date").cast(pl.Date))


@pytest.fixture()
def tmp_store(tmp_path: Path) -> DataStore:
    return DataStore(base_path=tmp_path / "store")


# ---------------------------------------------------------------------------
# Week 2 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def cointegrated_pair_prices() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Two cointegrated price series for pairs trading tests.

    Series B = 2.0 * Series A + noise, so hedge_ratio ≈ 2.0.
    """
    rng = np.random.default_rng(55)
    n = 500
    start = date(2022, 1, 3)
    dates = _business_dates(start, n)

    common = np.cumsum(rng.normal(0.0, 0.5, n))
    prices_a = 100.0 + common + rng.normal(0.0, 0.3, n)
    prices_b = 200.0 + 2.0 * common + rng.normal(0.0, 0.3, n)

    df_a = pl.DataFrame({
        "date": dates,
        "close": prices_a.tolist(),
    }).with_columns(pl.col("date").cast(pl.Date))

    df_b = pl.DataFrame({
        "date": dates,
        "close": prices_b.tolist(),
    }).with_columns(pl.col("date").cast(pl.Date))

    return df_a, df_b


@pytest.fixture(scope="session")
def sample_signals_df() -> pl.DataFrame:
    """Pre-built signals DataFrame for backtest engine tests."""
    rng = np.random.default_rng(77)
    n = 200
    start = date(2022, 1, 3)
    dates = _business_dates(start, n)

    directions = rng.choice([-1.0, 0.0, 1.0], size=n, p=[0.3, 0.4, 0.3])
    confidences = rng.uniform(0.3, 1.0, size=n)
    confidences[directions == 0.0] = 1.0

    return pl.DataFrame({
        "date": dates,
        "ticker": ["AAPL"] * n,
        "direction": directions.tolist(),
        "confidence": confidences.tolist(),
    }).with_columns(pl.col("date").cast(pl.Date))


@pytest.fixture(scope="session")
def bullish_prices() -> pl.DataFrame:
    """Steadily rising prices (1% daily) for testing long-only signals."""
    n = 200
    start = date(2022, 1, 3)
    dates = _business_dates(start, n)
    close = 100.0 * np.exp(np.cumsum(np.full(n, 0.01)))

    return pl.DataFrame({
        "date": dates,
        "ticker": ["AAPL"] * n,
        "open": close.tolist(),
        "high": (close * 1.005).tolist(),
        "low": (close * 0.995).tolist(),
        "close": close.tolist(),
        "volume": [1_000_000.0] * n,
    }).with_columns(pl.col("date").cast(pl.Date))


@pytest.fixture(scope="session")
def multi_ticker_ohlcv() -> pl.DataFrame:
    """OHLCV data for two tickers, for multi-ticker backtest tests."""
    rng = np.random.default_rng(88)
    n = 200
    start = date(2022, 1, 3)
    dates = _business_dates(start, n)

    frames = []
    for ticker, seed_offset in [("AAPL", 0), ("MSFT", 100)]:
        rng_t = np.random.default_rng(88 + seed_offset)
        log_r = rng_t.normal(0.0003, 0.012, size=n)
        close = 100.0 * np.exp(np.cumsum(log_r))
        frames.append(pl.DataFrame({
            "date": dates,
            "ticker": [ticker] * n,
            "open": close.tolist(),
            "high": (close * 1.01).tolist(),
            "low": (close * 0.99).tolist(),
            "close": close.tolist(),
            "volume": [1_000_000.0] * n,
        }))

    return pl.concat(frames).with_columns(pl.col("date").cast(pl.Date)).sort(["date", "ticker"])
