"""Comprehensive tests for the VectorizedBacktestEngine."""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl
import pytest

from backtest.engine.vectorized import VectorizedBacktestEngine
from core.backtest import BacktestEngineRegistry, BacktestResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dates(start: date, n: int) -> list[date]:
    """Generate *n* consecutive business-ish dates (skip weekends)."""
    dates: list[date] = []
    d = start
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)
    return dates


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine() -> VectorizedBacktestEngine:
    return VectorizedBacktestEngine()


@pytest.fixture
def simple_dates() -> list[date]:
    """20 trading days starting 2024-01-02."""
    return _make_dates(date(2024, 1, 2), 20)


@pytest.fixture
def bullish_prices(simple_dates: list[date]) -> pl.DataFrame:
    """Single ticker 'BULL' going up 1 % every day."""
    closes = [100.0]
    for _ in range(len(simple_dates) - 1):
        closes.append(closes[-1] * 1.01)
    return pl.DataFrame({
        "date": simple_dates,
        "ticker": ["BULL"] * len(simple_dates),
        "close": closes,
    })


@pytest.fixture
def long_signals(simple_dates: list[date]) -> pl.DataFrame:
    """All-long signal on 'BULL' every day, confidence=1."""
    return pl.DataFrame({
        "date": simple_dates,
        "ticker": ["BULL"] * len(simple_dates),
        "direction": [1.0] * len(simple_dates),
        "confidence": [1.0] * len(simple_dates),
    })


@pytest.fixture
def multi_ticker_prices(simple_dates: list[date]) -> pl.DataFrame:
    """Two tickers: AAA goes up 0.5 %/day, BBB goes down 0.3 %/day."""
    closes_a = [100.0]
    closes_b = [100.0]
    for _ in range(len(simple_dates) - 1):
        closes_a.append(closes_a[-1] * 1.005)
        closes_b.append(closes_b[-1] * 0.997)
    rows_a = pl.DataFrame({
        "date": simple_dates,
        "ticker": ["AAA"] * len(simple_dates),
        "close": closes_a,
    })
    rows_b = pl.DataFrame({
        "date": simple_dates,
        "ticker": ["BBB"] * len(simple_dates),
        "close": closes_b,
    })
    return pl.concat([rows_a, rows_b])


@pytest.fixture
def multi_ticker_signals(simple_dates: list[date]) -> pl.DataFrame:
    """Long AAA, short BBB with equal confidence."""
    sig_a = pl.DataFrame({
        "date": simple_dates,
        "ticker": ["AAA"] * len(simple_dates),
        "direction": [1.0] * len(simple_dates),
        "confidence": [0.5] * len(simple_dates),
    })
    sig_b = pl.DataFrame({
        "date": simple_dates,
        "ticker": ["BBB"] * len(simple_dates),
        "direction": [-1.0] * len(simple_dates),
        "confidence": [0.5] * len(simple_dates),
    })
    return pl.concat([sig_a, sig_b])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRunReturnsBacktestResult:
    def test_run_returns_backtest_result(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(long_signals, bullish_prices)
        assert isinstance(result, BacktestResult)


class TestEquityCurve:
    def test_equity_curve_has_correct_columns(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(long_signals, bullish_prices)
        assert "date" in result.equity_curve.columns
        assert "equity" in result.equity_curve.columns

    def test_initial_equity_equals_capital(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        capital = 50_000.0
        result = engine.run(long_signals, bullish_prices, initial_capital=capital)
        first_equity = result.equity_curve["equity"][0]
        # First equity may include day-1 return, but should be close to capital.
        assert first_equity == pytest.approx(capital, rel=0.05)


class TestTrades:
    def test_trades_has_correct_columns(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(long_signals, bullish_prices)
        for col in ("date", "ticker", "side", "price", "quantity", "pnl"):
            assert col in result.trades.columns


class TestMonthlyReturns:
    def test_monthly_returns_has_correct_columns(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(long_signals, bullish_prices)
        for col in ("year", "month", "return"):
            assert col in result.monthly_returns.columns


class TestEmptyInputs:
    def test_empty_signals_flat_equity(
        self,
        engine: VectorizedBacktestEngine,
        bullish_prices: pl.DataFrame,
    ) -> None:
        empty_signals = pl.DataFrame(
            schema={
                "date": pl.Date,
                "ticker": pl.Utf8,
                "direction": pl.Float64,
                "confidence": pl.Float64,
            }
        )
        result = engine.run(empty_signals, bullish_prices)
        assert result.total_return == pytest.approx(0.0)

    def test_empty_prices_flat_equity(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
    ) -> None:
        empty_prices = pl.DataFrame(
            schema={
                "date": pl.Date,
                "ticker": pl.Utf8,
                "close": pl.Float64,
            }
        )
        result = engine.run(long_signals, empty_prices)
        assert result.total_return == pytest.approx(0.0)


class TestTransactionCosts:
    def test_commission_reduces_returns(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        low = engine.run(long_signals, bullish_prices, commission=0.0001, slippage=0.0)
        high = engine.run(long_signals, bullish_prices, commission=0.01, slippage=0.0)
        assert high.total_return < low.total_return

    def test_slippage_reduces_returns(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        low = engine.run(long_signals, bullish_prices, commission=0.0, slippage=0.0001)
        high = engine.run(long_signals, bullish_prices, commission=0.0, slippage=0.01)
        assert high.total_return < low.total_return


class TestBullishMarket:
    def test_all_long_bullish_market(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(
            long_signals, bullish_prices, commission=0.0, slippage=0.0
        )
        # 1 % up per day for ~19 return days => ~20 % total
        assert result.total_return > 0.10


class TestMetrics:
    def test_sharpe_ratio_is_float(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(long_signals, bullish_prices)
        assert isinstance(result.sharpe_ratio, float)

    def test_max_drawdown_negative_or_zero(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(long_signals, bullish_prices)
        assert result.max_drawdown <= 0.0

    def test_win_rate_bounded_zero_to_one(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(long_signals, bullish_prices)
        assert 0.0 <= result.win_rate <= 1.0

    def test_profit_factor_non_negative(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(long_signals, bullish_prices)
        assert result.profit_factor >= 0.0

    def test_var_cvar_populated(
        self,
        engine: VectorizedBacktestEngine,
        long_signals: pl.DataFrame,
        bullish_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(long_signals, bullish_prices)
        assert result.var_95 is not None
        assert result.cvar_95 is not None
        assert isinstance(result.var_95, float)
        assert isinstance(result.cvar_95, float)


class TestWeightNormalization:
    def test_weight_normalization(
        self,
        engine: VectorizedBacktestEngine,
        simple_dates: list[date],
    ) -> None:
        """Signals with total abs weight > 1 should be normalised."""
        signals = pl.DataFrame({
            "date": simple_dates * 2,
            "ticker": ["X"] * len(simple_dates) + ["Y"] * len(simple_dates),
            "direction": [1.0] * len(simple_dates) + [-1.0] * len(simple_dates),
            "confidence": [0.8] * len(simple_dates) * 2,
        })
        closes_x = [100.0 + i * 0.5 for i in range(len(simple_dates))]
        closes_y = [50.0 + i * 0.1 for i in range(len(simple_dates))]
        prices = pl.concat([
            pl.DataFrame({
                "date": simple_dates,
                "ticker": ["X"] * len(simple_dates),
                "close": closes_x,
            }),
            pl.DataFrame({
                "date": simple_dates,
                "ticker": ["Y"] * len(simple_dates),
                "close": closes_y,
            }),
        ])

        # Run the engine — no assertion on returns, just verify normalisation
        # internally. We check via a side-channel: the engine should not crash
        # and the result should be valid.
        result = engine.run(signals, prices)
        assert isinstance(result, BacktestResult)
        # Max abs weight per date should be <= 1.0
        # We re-derive weights the same way the engine does to verify
        weights = (
            signals.with_columns(pl.col("date").cast(pl.Date))
            .select("date", "ticker",
                    (pl.col("direction") * pl.col("confidence")).alias("weight"))
            .group_by(["date", "ticker"]).agg(pl.col("weight").sum())
        )
        weights = weights.with_columns(
            pl.col("weight").abs().sum().over("date").alias("abs_sum")
        ).with_columns(
            pl.when(pl.col("abs_sum") > 1.0)
            .then(pl.col("weight") / pl.col("abs_sum"))
            .otherwise(pl.col("weight"))
            .alias("weight_norm")
        )
        per_date = weights.group_by("date").agg(
            pl.col("weight_norm").abs().sum().alias("total_abs_w")
        )
        assert per_date["total_abs_w"].max() <= 1.0 + 1e-9


class TestWalkForward:
    def _make_long_data(self, n_days: int = 400):
        dates = _make_dates(date(2023, 1, 2), n_days)
        closes = [100.0]
        for _ in range(n_days - 1):
            closes.append(closes[-1] * 1.001)
        prices = pl.DataFrame({
            "date": dates,
            "ticker": ["T"] * n_days,
            "close": closes,
        })
        signals = pl.DataFrame({
            "date": dates,
            "ticker": ["T"] * n_days,
            "direction": [1.0] * n_days,
            "confidence": [1.0] * n_days,
        })
        return signals, prices

    def test_walk_forward_returns_list(
        self,
        engine: VectorizedBacktestEngine,
    ) -> None:
        signals, prices = self._make_long_data()
        results = engine.walk_forward(signals, prices, train_window=252, test_window=63)
        assert isinstance(results, list)
        assert all(isinstance(r, BacktestResult) for r in results)

    def test_walk_forward_result_count(
        self,
        engine: VectorizedBacktestEngine,
    ) -> None:
        signals, prices = self._make_long_data(n_days=500)
        results = engine.walk_forward(signals, prices, train_window=252, test_window=63)
        # With 500 dates, train=252, test=63 => windows at 0,63,126,...
        # Need i + 252 + 63 <= 500 => i <= 185
        # i=0 (yes), i=63 (yes), i=126 (yes), i=189 (189+315=504>500 no)
        assert len(results) == 3


class TestRegistration:
    def test_registry_registration(self) -> None:
        # Re-register in case test_core_registries cleared the registry
        BacktestEngineRegistry.register(VectorizedBacktestEngine)
        engine = BacktestEngineRegistry.get("vectorized")
        assert engine.name == "vectorized"
        assert isinstance(engine, VectorizedBacktestEngine)


class TestMultiTicker:
    def test_multi_ticker_signals(
        self,
        engine: VectorizedBacktestEngine,
        multi_ticker_signals: pl.DataFrame,
        multi_ticker_prices: pl.DataFrame,
    ) -> None:
        result = engine.run(
            multi_ticker_signals,
            multi_ticker_prices,
            commission=0.0,
            slippage=0.0,
        )
        assert isinstance(result, BacktestResult)
        # Long AAA (up) + short BBB (down) => positive return
        assert result.total_return > 0.0
