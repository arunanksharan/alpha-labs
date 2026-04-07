"""Tests for risk/manager.py — RiskManager."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from core.risk import RiskAssessment
from core.strategies import Signal
from risk.manager import RiskManager


@pytest.fixture
def manager() -> RiskManager:
    return RiskManager(max_position_pct=0.10, max_drawdown_pct=0.15)


@pytest.fixture
def empty_positions() -> pl.DataFrame:
    return pl.DataFrame(schema={"ticker": pl.Utf8, "weight": pl.Float64})


class TestEvaluate:
    def test_returns_risk_assessment(self, manager: RiskManager, empty_positions: pl.DataFrame) -> None:
        signals = [Signal(ticker="AAPL", date="2022-01-03", direction=1.0, confidence=0.05)]
        result = manager.evaluate(signals, empty_positions, 100_000.0)
        assert isinstance(result, RiskAssessment)

    def test_empty_signals(self, manager: RiskManager, empty_positions: pl.DataFrame) -> None:
        result = manager.evaluate([], empty_positions, 100_000.0)
        assert len(result.approved_signals) == 0
        assert len(result.rejected_signals) == 0

    def test_small_signal_approved(self, manager: RiskManager, empty_positions: pl.DataFrame) -> None:
        signals = [Signal(ticker="AAPL", date="2022-01-03", direction=1.0, confidence=0.05)]
        result = manager.evaluate(signals, empty_positions, 100_000.0)
        assert len(result.approved_signals) == 1
        assert len(result.rejected_signals) == 0

    def test_large_signal_capped(self, manager: RiskManager, empty_positions: pl.DataFrame) -> None:
        # direction=1.0, confidence=0.5 → weight=0.5, exceeds max_position_pct=0.10
        signals = [Signal(ticker="AAPL", date="2022-01-03", direction=1.0, confidence=0.5)]
        result = manager.evaluate(signals, empty_positions, 100_000.0)
        assert len(result.approved_signals) == 1
        assert result.approved_signals[0].confidence <= 0.10
        assert len(result.warnings) > 0

    def test_exposure_limit_rejects_excess(self, manager: RiskManager, empty_positions: pl.DataFrame) -> None:
        # 15 signals each at 0.08 weight → total 1.20, some should be rejected
        signals = [
            Signal(ticker=f"T{i}", date="2022-01-03", direction=1.0, confidence=0.08)
            for i in range(15)
        ]
        result = manager.evaluate(signals, empty_positions, 100_000.0)
        assert len(result.rejected_signals) > 0
        total_approved = sum(
            abs(s.direction * s.confidence) for s in result.approved_signals
        )
        assert total_approved <= 1.0 + 1e-9

    def test_max_position_size_in_result(self, manager: RiskManager, empty_positions: pl.DataFrame) -> None:
        result = manager.evaluate([], empty_positions, 100_000.0)
        assert result.max_position_size == pytest.approx(10_000.0)

    def test_portfolio_var_computed(self, manager: RiskManager, empty_positions: pl.DataFrame) -> None:
        signals = [Signal(ticker="AAPL", date="2022-01-03", direction=1.0, confidence=0.05)]
        result = manager.evaluate(signals, empty_positions, 100_000.0)
        assert result.portfolio_var <= 0.0


class TestCalculatePositionSize:
    def test_basic_sizing(self, manager: RiskManager) -> None:
        sig = Signal(ticker="AAPL", date="2022-01-03", direction=1.0, confidence=0.05)
        size = manager.calculate_position_size(sig, 100_000.0, current_risk=0.0)
        assert size == pytest.approx(5_000.0)

    def test_capped_at_max_position(self, manager: RiskManager) -> None:
        sig = Signal(ticker="AAPL", date="2022-01-03", direction=1.0, confidence=0.50)
        size = manager.calculate_position_size(sig, 100_000.0, current_risk=0.0)
        assert size <= 10_000.0 + 1e-9  # max_position_pct * capital

    def test_reduces_with_high_current_risk(self, manager: RiskManager) -> None:
        sig = Signal(ticker="AAPL", date="2022-01-03", direction=1.0, confidence=0.05)
        size_low_risk = manager.calculate_position_size(sig, 100_000.0, current_risk=0.0)
        size_high_risk = manager.calculate_position_size(sig, 100_000.0, current_risk=0.10)
        assert size_high_risk < size_low_risk

    def test_zero_at_max_drawdown(self, manager: RiskManager) -> None:
        sig = Signal(ticker="AAPL", date="2022-01-03", direction=1.0, confidence=0.05)
        size = manager.calculate_position_size(sig, 100_000.0, current_risk=0.15)
        assert size == pytest.approx(0.0)


class TestCircuitBreakers:
    def test_allows_trading_within_limits(self, manager: RiskManager) -> None:
        equity = pl.DataFrame({
            "date": [date(2022, 1, i) for i in range(1, 11)],
            "equity": [100_000.0 + i * 1000 for i in range(10)],
        })
        assert manager.check_circuit_breakers(equity) is True

    def test_triggers_on_drawdown(self, manager: RiskManager) -> None:
        # Peak at 100K, drops to 80K → 20% drawdown, exceeds 15% limit
        equity = pl.DataFrame({
            "date": [date(2022, 1, i) for i in range(1, 6)],
            "equity": [100_000.0, 100_000.0, 95_000.0, 85_000.0, 80_000.0],
        })
        assert manager.check_circuit_breakers(equity) is False

    def test_allows_on_borderline_drawdown(self, manager: RiskManager) -> None:
        # Peak 100K, current 86K → 14% drawdown, within 15% limit
        equity = pl.DataFrame({
            "date": [date(2022, 1, i) for i in range(1, 4)],
            "equity": [100_000.0, 95_000.0, 86_000.0],
        })
        assert manager.check_circuit_breakers(equity) is True

    def test_empty_equity_allows_trading(self, manager: RiskManager) -> None:
        equity = pl.DataFrame(schema={"date": pl.Date, "equity": pl.Float64})
        assert manager.check_circuit_breakers(equity) is True

    def test_single_row_allows_trading(self, manager: RiskManager) -> None:
        equity = pl.DataFrame({
            "date": [date(2022, 1, 1)],
            "equity": [100_000.0],
        })
        assert manager.check_circuit_breakers(equity) is True

    def test_recovery_after_drawdown(self, manager: RiskManager) -> None:
        # Drawdown to 14%, then recovers — should still allow trading
        equity = pl.DataFrame({
            "date": [date(2022, 1, i) for i in range(1, 6)],
            "equity": [100_000.0, 90_000.0, 86_000.0, 92_000.0, 98_000.0],
        })
        assert manager.check_circuit_breakers(equity) is True
