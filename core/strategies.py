"""Base strategy interfaces.

A strategy consumes features and produces trading signals (position targets).
Strategies are backtestable and must declare their required features.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import polars as pl


@dataclass
class Signal:
    """A trading signal produced by a strategy."""

    ticker: str
    date: str
    direction: float  # -1.0 to 1.0 (short to long)
    confidence: float  # 0.0 to 1.0
    metadata: dict | None = None


class BaseStrategy(ABC):
    """Interface for all trading strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name."""

    @property
    @abstractmethod
    def required_features(self) -> list[str]:
        """List of feature names this strategy requires."""

    @abstractmethod
    def generate_signals(self, features: pl.DataFrame) -> list[Signal]:
        """Generate trading signals from computed features.

        Args:
            features: DataFrame with date, ticker, and feature columns.

        Returns:
            List of Signal objects.
        """

    @abstractmethod
    def get_positions(self, signals: list[Signal], capital: float) -> pl.DataFrame:
        """Convert signals into target positions (ticker, weight, shares).

        Args:
            signals: List of signals from generate_signals().
            capital: Available capital for allocation.

        Returns:
            DataFrame with columns: ticker, weight, target_shares, target_value.
        """


class StrategyRegistry:
    """Registry for available strategies."""

    _strategies: dict[str, type[BaseStrategy]] = {}

    @classmethod
    def register(cls, strategy_cls: type[BaseStrategy]) -> type[BaseStrategy]:
        """Use as decorator: @StrategyRegistry.register"""
        instance = strategy_cls()
        cls._strategies[instance.name] = strategy_cls
        return strategy_cls

    @classmethod
    def get(cls, name: str, **kwargs) -> BaseStrategy:
        if name not in cls._strategies:
            available = ", ".join(cls._strategies.keys())
            raise KeyError(f"Strategy '{name}' not found. Available: {available}")
        return cls._strategies[name](**kwargs)

    @classmethod
    def list_strategies(cls) -> list[str]:
        return list(cls._strategies.keys())
