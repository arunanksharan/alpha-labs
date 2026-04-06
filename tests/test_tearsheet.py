"""Tests for backtest/reports/tearsheet.py."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from matplotlib.figure import Figure

from backtest.reports.tearsheet import TearSheet
from core.backtest import BacktestResult


@pytest.fixture
def sample_backtest_result() -> BacktestResult:
    """A realistic BacktestResult for tear sheet testing."""
    n = 252
    dates = [date(2022, 1, 3) + timedelta(days=i) for i in range(n)]
    rng = np.random.default_rng(42)
    daily_returns = rng.normal(0.0003, 0.01, n)
    equity = 100_000.0 * np.exp(np.cumsum(daily_returns))

    equity_curve = pl.DataFrame({
        "date": dates,
        "equity": equity.tolist(),
    }).with_columns(pl.col("date").cast(pl.Date))

    trades = pl.DataFrame({
        "date": dates[:20],
        "ticker": ["AAPL"] * 20,
        "side": (["buy"] * 10 + ["sell"] * 10),
        "price": rng.uniform(140, 160, 20).tolist(),
        "quantity": rng.uniform(10, 100, 20).tolist(),
        "pnl": rng.normal(50, 200, 20).tolist(),
    }).with_columns(pl.col("date").cast(pl.Date))

    # Monthly returns
    monthly_data = []
    for month in range(1, 13):
        monthly_data.append({"year": 2022, "month": month, "return": float(rng.normal(0.01, 0.03))})
    monthly_returns = pl.DataFrame(monthly_data)

    return BacktestResult(
        strategy_name="mean_reversion_test",
        start_date="2022-01-03",
        end_date="2022-12-31",
        total_return=0.12,
        annualized_return=0.12,
        sharpe_ratio=1.2,
        sortino_ratio=1.8,
        max_drawdown=-0.08,
        calmar_ratio=1.5,
        win_rate=0.55,
        profit_factor=1.3,
        equity_curve=equity_curve,
        trades=trades,
        monthly_returns=monthly_returns,
        var_95=-0.015,
        cvar_95=-0.022,
    )


@pytest.fixture
def empty_backtest_result() -> BacktestResult:
    """BacktestResult with empty DataFrames."""
    return BacktestResult(
        strategy_name="empty_test",
        start_date="2022-01-03",
        end_date="2022-01-03",
        total_return=0.0,
        annualized_return=0.0,
        sharpe_ratio=0.0,
        sortino_ratio=0.0,
        max_drawdown=0.0,
        calmar_ratio=0.0,
        win_rate=0.0,
        profit_factor=0.0,
        equity_curve=pl.DataFrame(schema={"date": pl.Date, "equity": pl.Float64}),
        trades=pl.DataFrame(),
        monthly_returns=pl.DataFrame(schema={"year": pl.Int64, "month": pl.Int64, "return": pl.Float64}),
    )


class TestPlots:
    def test_equity_curve_returns_figure(self, sample_backtest_result: BacktestResult) -> None:
        ts = TearSheet(sample_backtest_result)
        fig = ts.equity_curve_plot()
        assert isinstance(fig, Figure)
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_drawdown_returns_figure(self, sample_backtest_result: BacktestResult) -> None:
        ts = TearSheet(sample_backtest_result)
        fig = ts.drawdown_plot()
        assert isinstance(fig, Figure)
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_monthly_heatmap_returns_figure(self, sample_backtest_result: BacktestResult) -> None:
        ts = TearSheet(sample_backtest_result)
        fig = ts.monthly_returns_heatmap()
        assert isinstance(fig, Figure)
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_metrics_table_returns_figure(self, sample_backtest_result: BacktestResult) -> None:
        ts = TearSheet(sample_backtest_result)
        fig = ts.metrics_table()
        assert isinstance(fig, Figure)
        import matplotlib.pyplot as plt
        plt.close(fig)


class TestSave:
    def test_save_html_creates_file(
        self, sample_backtest_result: BacktestResult, tmp_path: Path
    ) -> None:
        ts = TearSheet(sample_backtest_result)
        html_path = tmp_path / "tearsheet.html"
        ts.save_html(html_path)
        assert html_path.exists()
        content = html_path.read_text()
        assert "mean_reversion_test" in content

    def test_save_html_contains_images(
        self, sample_backtest_result: BacktestResult, tmp_path: Path
    ) -> None:
        ts = TearSheet(sample_backtest_result)
        html_path = tmp_path / "tearsheet.html"
        ts.save_html(html_path)
        content = html_path.read_text()
        assert "data:image/png;base64," in content

    def test_save_png_creates_files(
        self, sample_backtest_result: BacktestResult, tmp_path: Path
    ) -> None:
        ts = TearSheet(sample_backtest_result)
        png_dir = tmp_path / "plots"
        paths = ts.save_png(png_dir)
        assert len(paths) == 4
        for p in paths:
            assert p.exists()
            assert p.suffix == ".png"


class TestEdgeCases:
    def test_empty_equity_curve(self, empty_backtest_result: BacktestResult) -> None:
        ts = TearSheet(empty_backtest_result)
        fig = ts.equity_curve_plot()
        assert isinstance(fig, Figure)
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_empty_monthly_returns(self, empty_backtest_result: BacktestResult) -> None:
        ts = TearSheet(empty_backtest_result)
        fig = ts.monthly_returns_heatmap()
        assert isinstance(fig, Figure)
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_save_html_with_empty_data(
        self, empty_backtest_result: BacktestResult, tmp_path: Path
    ) -> None:
        ts = TearSheet(empty_backtest_result)
        html_path = tmp_path / "empty_tearsheet.html"
        ts.save_html(html_path)
        assert html_path.exists()
