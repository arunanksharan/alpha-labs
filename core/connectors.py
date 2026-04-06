"""Base connector interfaces for all external data sources.

To add a new data source:
1. Subclass the appropriate BaseConnector
2. Implement required methods
3. Register via ConnectorRegistry.register()
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

import polars as pl


class BaseConnector(ABC):
    """Root interface for all external connectors."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection / validate credentials."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the connector is operational."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable connector name."""


class BaseMarketDataConnector(BaseConnector):
    """Interface for price/OHLCV data sources (yfinance, Tiingo, Alpha Vantage, etc.)."""

    @abstractmethod
    def fetch_ohlcv(
        self,
        ticker: str,
        start: date,
        end: date,
        interval: str = "1d",
    ) -> pl.DataFrame:
        """Fetch OHLCV data. Must return columns: date, open, high, low, close, volume."""

    @abstractmethod
    def fetch_multiple(
        self,
        tickers: list[str],
        start: date,
        end: date,
        interval: str = "1d",
    ) -> dict[str, pl.DataFrame]:
        """Fetch OHLCV for multiple tickers."""

    @abstractmethod
    def supported_intervals(self) -> list[str]:
        """Return list of supported intervals (e.g., ['1m', '5m', '1h', '1d'])."""


class BaseFundamentalConnector(BaseConnector):
    """Interface for fundamental data sources (SEC EDGAR, SimFin, FMP, etc.)."""

    @abstractmethod
    def fetch_financials(
        self,
        ticker: str,
        statement: str = "income",
        period: str = "quarterly",
    ) -> pl.DataFrame:
        """Fetch financial statements. statement: income | balance | cashflow."""

    @abstractmethod
    def fetch_ratios(self, ticker: str) -> dict[str, Any]:
        """Fetch key financial ratios (P/E, EV/EBITDA, ROE, etc.)."""


class BaseAltDataConnector(BaseConnector):
    """Interface for alternative data sources (news, sentiment, social, etc.)."""

    @abstractmethod
    def fetch_data(
        self,
        query: str,
        start: date,
        end: date,
    ) -> pl.DataFrame:
        """Fetch alternative data. Schema varies by connector."""


class BaseExecutionConnector(BaseConnector):
    """Interface for execution targets (Alpaca, IBKR, paper trading, etc.)."""

    @abstractmethod
    def submit_order(
        self,
        ticker: str,
        quantity: float,
        side: str,
        order_type: str = "market",
        limit_price: float | None = None,
    ) -> dict[str, Any]:
        """Submit an order. Returns order confirmation dict."""

    @abstractmethod
    def get_positions(self) -> pl.DataFrame:
        """Return current positions."""

    @abstractmethod
    def get_portfolio_value(self) -> float:
        """Return current total portfolio value."""


class ConnectorRegistry:
    """Registry for discovering and instantiating connectors.

    Usage:
        registry = ConnectorRegistry()
        registry.register("yfinance", YFinanceConnector)
        connector = registry.get("yfinance")
    """

    _connectors: dict[str, type[BaseConnector]] = {}

    @classmethod
    def register(cls, name: str, connector_cls: type[BaseConnector]) -> None:
        cls._connectors[name] = connector_cls

    @classmethod
    def get(cls, name: str, **kwargs: Any) -> BaseConnector:
        if name not in cls._connectors:
            available = ", ".join(cls._connectors.keys())
            raise KeyError(f"Connector '{name}' not found. Available: {available}")
        return cls._connectors[name](**kwargs)

    @classmethod
    def list_connectors(cls) -> list[str]:
        return list(cls._connectors.keys())
