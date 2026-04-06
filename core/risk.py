"""Base risk management interfaces.

Risk management is NOT optional. Every strategy must pass through the risk layer
before execution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import polars as pl

from core.strategies import Signal


@dataclass
class RiskAssessment:
    """Output of risk evaluation for a set of signals."""

    approved_signals: list[Signal]
    rejected_signals: list[Signal]
    portfolio_var: float
    portfolio_cvar: float
    max_position_size: float
    warnings: list[str]


class BaseRiskManager(ABC):
    """Interface for risk management implementations."""

    @abstractmethod
    def evaluate(
        self,
        signals: list[Signal],
        current_positions: pl.DataFrame,
        portfolio_value: float,
    ) -> RiskAssessment:
        """Evaluate signals against risk constraints.

        May reject signals, reduce position sizes, or add warnings.
        """

    @abstractmethod
    def calculate_position_size(
        self,
        signal: Signal,
        portfolio_value: float,
        current_risk: float,
    ) -> float:
        """Calculate appropriate position size given risk budget."""

    @abstractmethod
    def check_circuit_breakers(
        self,
        equity_curve: pl.DataFrame,
    ) -> bool:
        """Return False if circuit breaker is triggered (stop trading)."""
