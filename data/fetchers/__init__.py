"""Data fetcher connectors — auto-registered on import.

Importing this package registers all connectors with ConnectorRegistry.
"""

# Each connector module registers itself at import time via
# ConnectorRegistry.register() at module level.
from data.fetchers.yfinance_connector import YFinanceConnector  # noqa: F401
from data.fetchers.fred_connector import FREDConnector  # noqa: F401
from data.fetchers.edgar_connector import EdgarConnector  # noqa: F401
