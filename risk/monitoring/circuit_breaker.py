"""Drawdown monitor with circuit breakers.

Tracks portfolio equity against its high-water mark and triggers a circuit
breaker when the drawdown exceeds a configurable threshold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import polars as pl

from config.settings import settings


@dataclass
class CircuitBreakerStatus:
    """Snapshot of the circuit breaker state after an equity update."""

    is_triggered: bool
    current_drawdown: float
    max_allowed_drawdown: float
    peak_equity: float
    current_equity: float
    trigger_reason: str | None = None


@dataclass
class _HistoryEntry:
    timestamp: datetime
    equity: float
    drawdown: float
    peak: float
    triggered: bool


class DrawdownMonitor:
    """Track drawdowns and trigger circuit breakers.

    Parameters
    ----------
    max_drawdown_pct : float | None
        Maximum tolerated drawdown expressed as a positive fraction (e.g.
        ``0.15`` for 15 %).  Defaults to ``settings.risk.max_drawdown_pct``.
    warning_threshold_pct : float
        Fraction of *max_drawdown_pct* at which a warning is emitted. For
        example ``0.5`` means a warning fires when the drawdown reaches 50 %
        of the maximum allowed.
    """

    def __init__(
        self,
        max_drawdown_pct: float | None = None,
        warning_threshold_pct: float = 0.5,
    ) -> None:
        self.max_drawdown_pct: float = (
            max_drawdown_pct if max_drawdown_pct is not None else settings.risk.max_drawdown_pct
        )
        self.warning_threshold_pct: float = warning_threshold_pct

        self._peak_equity: float | None = None
        self._triggered: bool = False
        self._history: list[_HistoryEntry] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, equity: float) -> CircuitBreakerStatus:
        """Process a new equity observation.

        Updates the high-water mark, computes the current drawdown, and
        returns a :class:`CircuitBreakerStatus` indicating whether the
        circuit breaker has been triggered or a warning issued.
        """
        if self._peak_equity is None or equity > self._peak_equity:
            self._peak_equity = equity

        current_drawdown = (equity - self._peak_equity) / self._peak_equity  # <= 0

        trigger_reason: str | None = None

        # Circuit breaker check (drawdown is negative, threshold is positive)
        if abs(current_drawdown) >= self.max_drawdown_pct:
            self._triggered = True
            trigger_reason = (
                f"Drawdown {current_drawdown:.4f} exceeded maximum "
                f"allowed {-self.max_drawdown_pct:.4f}"
            )
        elif abs(current_drawdown) >= self.warning_threshold_pct * self.max_drawdown_pct:
            trigger_reason = (
                f"Warning: drawdown {current_drawdown:.4f} reached "
                f"{abs(current_drawdown) / self.max_drawdown_pct:.0%} of limit"
            )

        status = CircuitBreakerStatus(
            is_triggered=self._triggered,
            current_drawdown=current_drawdown,
            max_allowed_drawdown=self.max_drawdown_pct,
            peak_equity=self._peak_equity,
            current_equity=equity,
            trigger_reason=trigger_reason,
        )

        self._history.append(
            _HistoryEntry(
                timestamp=datetime.now(),
                equity=equity,
                drawdown=current_drawdown,
                peak=self._peak_equity,
                triggered=self._triggered,
            )
        )

        return status

    def check(self, equity_curve: pl.DataFrame) -> CircuitBreakerStatus:
        """Process an entire equity curve and return the final status.

        Parameters
        ----------
        equity_curve : pl.DataFrame
            Must contain columns ``date`` and ``equity``.
        """
        if "equity" not in equity_curve.columns:
            raise ValueError("equity_curve must contain an 'equity' column")

        equities = equity_curve["equity"].to_list()
        status: CircuitBreakerStatus | None = None
        for eq in equities:
            status = self.update(float(eq))
        if status is None:
            raise ValueError("equity_curve is empty")
        return status

    def reset(self) -> None:
        """Reset the monitor to its initial state."""
        self._peak_equity = None
        self._triggered = False
        self._history.clear()

    def get_history(self) -> pl.DataFrame:
        """Return a polars DataFrame of all recorded updates.

        Columns: ``timestamp``, ``equity``, ``drawdown``, ``peak``,
        ``triggered``.
        """
        if not self._history:
            return pl.DataFrame(
                schema={
                    "timestamp": pl.Datetime,
                    "equity": pl.Float64,
                    "drawdown": pl.Float64,
                    "peak": pl.Float64,
                    "triggered": pl.Boolean,
                }
            )
        return pl.DataFrame(
            {
                "timestamp": [e.timestamp for e in self._history],
                "equity": [e.equity for e in self._history],
                "drawdown": [e.drawdown for e in self._history],
                "peak": [e.peak for e in self._history],
                "triggered": [e.triggered for e in self._history],
            }
        )
