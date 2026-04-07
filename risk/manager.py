"""Risk manager — evaluates signals against risk constraints.

Implements BaseRiskManager. Integrates position sizing, drawdown monitoring,
and portfolio-level risk checks into a single evaluation pipeline.
"""

from __future__ import annotations

import logging
from copy import deepcopy

import numpy as np
import polars as pl

from analytics.returns import compute_max_drawdown, compute_returns, compute_var, compute_cvar
from config.settings import settings
from core.risk import BaseRiskManager, RiskAssessment
from core.strategies import Signal

logger = logging.getLogger(__name__)


class RiskManager(BaseRiskManager):
    """Production risk manager with position limits, drawdown breakers, and VaR checks.

    Parameters
    ----------
    max_position_pct:
        Maximum weight for any single position. Default from settings.
    max_portfolio_var:
        Maximum portfolio 1-day VaR (as a negative fraction). None = no limit.
    max_drawdown_pct:
        Circuit breaker threshold. Default from settings.
    max_correlation:
        Maximum pairwise correlation for new signals against existing positions.
    """

    def __init__(
        self,
        max_position_pct: float | None = None,
        max_portfolio_var: float | None = None,
        max_drawdown_pct: float | None = None,
        max_correlation: float = 0.85,
    ) -> None:
        self._max_position_pct = max_position_pct or settings.risk.max_position_pct
        self._max_portfolio_var = max_portfolio_var
        self._max_drawdown_pct = max_drawdown_pct or settings.risk.max_drawdown_pct
        self._max_correlation = max_correlation
        self._peak_equity: float | None = None

    def evaluate(
        self,
        signals: list[Signal],
        current_positions: pl.DataFrame,
        portfolio_value: float,
    ) -> RiskAssessment:
        """Evaluate signals against risk constraints.

        Checks applied (in order):
        1. Position size limits (cap each signal's implied weight)
        2. Total exposure limit (reject signals that push total > 100%)
        3. Portfolio VaR limit (if configured)

        Returns RiskAssessment with approved/rejected signals and warnings.
        """
        if not signals:
            return RiskAssessment(
                approved_signals=[],
                rejected_signals=[],
                portfolio_var=0.0,
                portfolio_cvar=0.0,
                max_position_size=self._max_position_pct * portfolio_value,
                warnings=[],
            )

        approved: list[Signal] = []
        rejected: list[Signal] = []
        warnings: list[str] = []

        current_exposure = self._total_exposure(current_positions)

        for signal in signals:
            implied_weight = abs(signal.direction * signal.confidence)

            # Check 1: Position size limit
            if implied_weight > self._max_position_pct:
                capped_confidence = self._max_position_pct / max(abs(signal.direction), 1e-10)
                capped_signal = Signal(
                    ticker=signal.ticker,
                    date=signal.date,
                    direction=signal.direction,
                    confidence=min(capped_confidence, signal.confidence),
                    metadata={**(signal.metadata or {}), "risk_capped": True},
                )
                approved.append(capped_signal)
                warnings.append(
                    f"{signal.ticker}: position capped from {implied_weight:.1%} to {self._max_position_pct:.1%}"
                )
                implied_weight = self._max_position_pct

            else:
                approved.append(deepcopy(signal))

            # Check 2: Total exposure limit
            current_exposure += implied_weight
            if current_exposure > 1.0:
                last = approved.pop()
                rejected.append(last)
                current_exposure -= implied_weight
                warnings.append(
                    f"{signal.ticker}: rejected — total exposure would exceed 100%"
                )

        # Compute portfolio risk metrics
        portfolio_var = self._estimate_portfolio_var(approved, portfolio_value)
        portfolio_cvar = portfolio_var * 1.4  # Rough CVaR ≈ 1.4x VaR for normal dist

        # Check 3: VaR limit
        if self._max_portfolio_var is not None and portfolio_var < self._max_portfolio_var:
            while approved and portfolio_var < self._max_portfolio_var:
                rejected_sig = approved.pop()
                rejected.append(rejected_sig)
                warnings.append(
                    f"{rejected_sig.ticker}: rejected — portfolio VaR exceeds limit"
                )
                portfolio_var = self._estimate_portfolio_var(approved, portfolio_value)

        return RiskAssessment(
            approved_signals=approved,
            rejected_signals=rejected,
            portfolio_var=portfolio_var,
            portfolio_cvar=portfolio_cvar,
            max_position_size=self._max_position_pct * portfolio_value,
            warnings=warnings,
        )

    def calculate_position_size(
        self,
        signal: Signal,
        portfolio_value: float,
        current_risk: float,
    ) -> float:
        """Calculate position size in dollars respecting risk budget.

        Uses volatility-adjusted sizing: size ∝ confidence / risk.
        """
        base_weight = abs(signal.direction * signal.confidence)
        capped_weight = min(base_weight, self._max_position_pct)

        # Scale down if current risk is already high
        if current_risk > 0:
            risk_factor = max(0.0, 1.0 - current_risk / self._max_drawdown_pct)
            capped_weight *= risk_factor

        return capped_weight * portfolio_value

    def check_circuit_breakers(
        self,
        equity_curve: pl.DataFrame,
    ) -> bool:
        """Return False if circuit breaker is triggered.

        Checks:
        1. Maximum drawdown threshold exceeded
        2. Equity below peak * (1 - max_drawdown_pct)
        """
        if equity_curve.is_empty() or "equity" not in equity_curve.columns:
            return True  # No data, allow trading

        equity_values = equity_curve["equity"]
        if len(equity_values) < 2:
            return True

        peak = equity_values.max()
        current = equity_values[-1]

        if peak is None or peak == 0:
            return True

        drawdown = (current - peak) / peak

        if drawdown < -self._max_drawdown_pct:
            logger.warning(
                "Circuit breaker TRIGGERED: drawdown %.2f%% exceeds max %.2f%%",
                drawdown * 100,
                self._max_drawdown_pct * 100,
            )
            return False

        return True

    def _total_exposure(self, positions: pl.DataFrame) -> float:
        """Sum of absolute weights in current positions."""
        if positions.is_empty() or "weight" not in positions.columns:
            return 0.0
        return float(positions["weight"].abs().sum())

    def _estimate_portfolio_var(
        self, signals: list[Signal], portfolio_value: float
    ) -> float:
        """Quick parametric VaR estimate from signal weights.

        Assumes 1% daily vol per position (conservative estimate).
        Uses sqrt(n) scaling for diversification.
        """
        if not signals:
            return 0.0

        total_exposure = sum(abs(s.direction * s.confidence) for s in signals)
        # Parametric VaR at 95%: -1.645 * portfolio_vol
        # Assume 1% daily vol per unit of exposure, sqrt(n) diversification
        n = len(signals)
        diversified_vol = total_exposure * 0.01 / max(1, n ** 0.5)
        return -1.645 * diversified_vol
