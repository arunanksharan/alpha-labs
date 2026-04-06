"""Central configuration for the quant research platform.

All settings are loaded from environment variables with sensible defaults.
No secrets in code — ever.
"""

from pathlib import Path
from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class DataSettings:
    """Data source configuration."""

    store_path: Path = Path("data/store")
    cache_path: Path = Path("data/cache")
    default_market_connector: str = "yfinance"
    default_start_date: str = "2015-01-01"


@dataclass(frozen=True)
class APIKeys:
    """API keys loaded from environment variables."""

    fred: str = field(default_factory=lambda: os.environ.get("FRED_API_KEY", ""))
    alpha_vantage: str = field(
        default_factory=lambda: os.environ.get("ALPHA_VANTAGE_API_KEY", "")
    )
    polygon: str = field(default_factory=lambda: os.environ.get("POLYGON_API_KEY", ""))
    tiingo: str = field(default_factory=lambda: os.environ.get("TIINGO_API_KEY", ""))
    fmp: str = field(default_factory=lambda: os.environ.get("FMP_API_KEY", ""))
    newsapi: str = field(default_factory=lambda: os.environ.get("NEWSAPI_KEY", ""))


@dataclass(frozen=True)
class BacktestSettings:
    """Default backtesting parameters."""

    initial_capital: float = 100_000.0
    commission: float = 0.001  # 10 bps
    slippage: float = 0.0005  # 5 bps
    risk_free_rate: float = 0.05  # Updated for current rate environment
    benchmark_ticker: str = "SPY"


@dataclass(frozen=True)
class RiskSettings:
    """Risk management defaults."""

    max_position_pct: float = 0.10  # Max 10% of portfolio in single position
    max_sector_pct: float = 0.30  # Max 30% in single sector
    max_drawdown_pct: float = 0.15  # Circuit breaker at 15% drawdown
    var_confidence: float = 0.95
    kelly_fraction: float = 0.25  # Quarter Kelly for safety


@dataclass(frozen=True)
class Settings:
    """Root settings object."""

    data: DataSettings = field(default_factory=DataSettings)
    api_keys: APIKeys = field(default_factory=APIKeys)
    backtest: BacktestSettings = field(default_factory=BacktestSettings)
    risk: RiskSettings = field(default_factory=RiskSettings)

    sec_edgar_user_agent: str = "QuantResearcher research@kuzushilabs.com"
    log_level: str = field(
        default_factory=lambda: os.environ.get("QR_LOG_LEVEL", "INFO")
    )


# Singleton
settings = Settings()
