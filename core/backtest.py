"""Base backtesting interfaces.

Pluggable backtest engines: swap between VectorBT, Qlib, Backtrader
without changing strategy code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import polars as pl


@dataclass
class BacktestResult:
    """Standardized backtest output regardless of engine."""

    strategy_name: str
    start_date: str
    end_date: str

    # Core metrics
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float

    # Detailed data
    equity_curve: pl.DataFrame  # date, equity
    trades: pl.DataFrame  # date, ticker, side, price, quantity, pnl
    monthly_returns: pl.DataFrame  # year, month, return

    # Optional advanced metrics
    information_ratio: float | None = None
    beta: float | None = None
    alpha: float | None = None
    var_95: float | None = None
    cvar_95: float | None = None

    # Metadata
    transaction_costs: float = 0.0
    slippage_model: str = "none"
    metadata: dict = field(default_factory=dict)


class BaseBacktestEngine(ABC):
    """Interface for backtesting engines (VectorBT, Qlib, Backtrader, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name."""

    @abstractmethod
    def run(
        self,
        signals: pl.DataFrame,
        prices: pl.DataFrame,
        initial_capital: float = 100_000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ) -> BacktestResult:
        """Run backtest with given signals against price data.

        Args:
            signals: DataFrame with date, ticker, direction, confidence columns.
            prices: OHLCV DataFrame with date, ticker, open, high, low, close, volume.
            initial_capital: Starting capital.
            commission: Commission per trade as fraction (0.001 = 0.1%).
            slippage: Slippage per trade as fraction.

        Returns:
            Standardized BacktestResult.
        """

    @abstractmethod
    def walk_forward(
        self,
        signals: pl.DataFrame,
        prices: pl.DataFrame,
        train_window: int = 252,
        test_window: int = 63,
        **kwargs,
    ) -> list[BacktestResult]:
        """Run walk-forward analysis (rolling train/test windows).

        Returns list of BacktestResults, one per test window.
        """


class BacktestEngineRegistry:
    """Registry for backtest engines."""

    _engines: dict[str, type[BaseBacktestEngine]] = {}

    @classmethod
    def register(cls, engine_cls: type[BaseBacktestEngine]) -> type[BaseBacktestEngine]:
        instance = engine_cls()
        cls._engines[instance.name] = engine_cls
        return engine_cls

    @classmethod
    def get(cls, name: str, **kwargs) -> BaseBacktestEngine:
        if name not in cls._engines:
            available = ", ".join(cls._engines.keys())
            raise KeyError(f"Engine '{name}' not found. Available: {available}")
        return cls._engines[name](**kwargs)

    @classmethod
    def list_engines(cls) -> list[str]:
        return list(cls._engines.keys())
