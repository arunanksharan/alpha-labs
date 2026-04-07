"""Tests for drawdown monitor and circuit breaker."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

import polars as pl
import pytest

from risk.monitoring.circuit_breaker import CircuitBreakerStatus, DrawdownMonitor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def monitor() -> DrawdownMonitor:
    return DrawdownMonitor(max_drawdown_pct=0.15, warning_threshold_pct=0.5)


@pytest.fixture()
def equity_curve_ok() -> pl.DataFrame:
    """Equity curve that stays within the 15% drawdown limit."""
    equities = [100.0, 102.0, 104.0, 101.0, 99.0, 100.0, 103.0]
    dates = [date(2023, 1, 2) + timedelta(days=i) for i in range(len(equities))]
    return pl.DataFrame({"date": dates, "equity": equities})


@pytest.fixture()
def equity_curve_breach() -> pl.DataFrame:
    """Equity curve that breaches the 15% drawdown limit."""
    equities = [100.0, 105.0, 95.0, 90.0, 88.0]  # 88/105 - 1 = -0.162
    dates = [date(2023, 1, 2) + timedelta(days=i) for i in range(len(equities))]
    return pl.DataFrame({"date": dates, "equity": equities})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNoTrigger:
    def test_no_trigger_within_limits(self, monitor: DrawdownMonitor) -> None:
        status = monitor.update(100.0)
        assert status.is_triggered is False
        assert status.trigger_reason is None

        status = monitor.update(98.0)
        assert status.is_triggered is False

    def test_no_trigger_on_new_highs(self, monitor: DrawdownMonitor) -> None:
        for eq in [100.0, 102.0, 104.0, 106.0]:
            status = monitor.update(eq)
        assert status.is_triggered is False
        assert status.current_drawdown == 0.0


class TestTrigger:
    def test_trigger_at_max_drawdown(self, monitor: DrawdownMonitor) -> None:
        monitor.update(100.0)
        # Drop exactly 15%
        status = monitor.update(85.0)
        assert status.is_triggered is True
        assert status.trigger_reason is not None
        assert "exceeded" in status.trigger_reason.lower() or "Drawdown" in status.trigger_reason

    def test_trigger_stays_latched(self, monitor: DrawdownMonitor) -> None:
        monitor.update(100.0)
        monitor.update(84.0)  # triggers
        # Even if equity recovers, circuit breaker stays latched
        status = monitor.update(100.0)
        assert status.is_triggered is True


class TestWarning:
    def test_warning_at_threshold(self, monitor: DrawdownMonitor) -> None:
        monitor.update(100.0)
        # 50% of 15% = 7.5% drawdown -> warn
        status = monitor.update(92.0)  # 8% drawdown > 7.5%
        assert status.is_triggered is False
        assert status.trigger_reason is not None
        assert "warning" in status.trigger_reason.lower()


class TestPeakTracking:
    def test_peak_tracking(self, monitor: DrawdownMonitor) -> None:
        monitor.update(100.0)
        monitor.update(105.0)
        status = monitor.update(103.0)
        assert status.peak_equity == 105.0
        assert status.current_drawdown == pytest.approx((103.0 - 105.0) / 105.0)


class TestDrawdownCalculation:
    def test_drawdown_calculation_correct(self, monitor: DrawdownMonitor) -> None:
        monitor.update(200.0)
        status = monitor.update(180.0)
        expected_dd = (180.0 - 200.0) / 200.0  # -0.10
        assert status.current_drawdown == pytest.approx(expected_dd)
        assert status.peak_equity == 200.0
        assert status.current_equity == 180.0


class TestReset:
    def test_reset_clears_state(self, monitor: DrawdownMonitor) -> None:
        monitor.update(100.0)
        monitor.update(80.0)  # trigger
        assert monitor._triggered is True

        monitor.reset()

        assert monitor._peak_equity is None
        assert monitor._triggered is False
        assert len(monitor._history) == 0

        status = monitor.update(50.0)
        assert status.is_triggered is False
        assert status.peak_equity == 50.0


class TestCheckEquityCurve:
    def test_check_equity_curve(
        self, monitor: DrawdownMonitor, equity_curve_ok: pl.DataFrame
    ) -> None:
        status = monitor.check(equity_curve_ok)
        assert status.is_triggered is False

    def test_check_equity_curve_breach(
        self, monitor: DrawdownMonitor, equity_curve_breach: pl.DataFrame
    ) -> None:
        status = monitor.check(equity_curve_breach)
        assert status.is_triggered is True

    def test_check_missing_column(self, monitor: DrawdownMonitor) -> None:
        df = pl.DataFrame({"date": [date(2023, 1, 1)], "value": [100.0]})
        with pytest.raises(ValueError, match="equity"):
            monitor.check(df)


class TestGetHistory:
    def test_get_history_tracks_updates(self, monitor: DrawdownMonitor) -> None:
        monitor.update(100.0)
        monitor.update(95.0)
        monitor.update(98.0)

        history = monitor.get_history()
        assert len(history) == 3
        assert history.columns == ["timestamp", "equity", "drawdown", "peak", "triggered"]
        assert history["equity"].to_list() == [100.0, 95.0, 98.0]
        assert history["peak"].to_list() == [100.0, 100.0, 100.0]

    def test_get_history_empty(self, monitor: DrawdownMonitor) -> None:
        history = monitor.get_history()
        assert len(history) == 0
        assert "equity" in history.columns


class TestDefaultFromSettings:
    def test_default_from_settings(self) -> None:
        monitor = DrawdownMonitor()
        assert monitor.max_drawdown_pct == 0.15  # from RiskSettings default
