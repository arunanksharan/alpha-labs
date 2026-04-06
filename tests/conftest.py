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
