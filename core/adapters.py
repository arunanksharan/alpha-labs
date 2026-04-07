"""Input adapters for MCP/API -- convert simple types to polars DataFrames.

These adapters bridge the JSON-native agent/API layer with the polars-native
internal computation layer. They handle CSV/JSON parsing, data fetching with
fallback, and signal preparation for the backtest engine.
"""

from __future__ import annotations

import io

import polars as pl


def csv_to_dataframe(csv_string: str) -> pl.DataFrame:
    """Parse CSV string into polars DataFrame."""
    return pl.read_csv(io.StringIO(csv_string))


def json_to_dataframe(data: list[dict]) -> pl.DataFrame:
    """Parse list of dicts into polars DataFrame."""
    return pl.DataFrame(data)


def dataframe_to_csv(df: pl.DataFrame) -> str:
    """Convert DataFrame to CSV string."""
    buf = io.StringIO()
    df.write_csv(buf)
    return buf.getvalue()


def fetch_and_prepare_prices(ticker: str, start: str, end: str) -> pl.DataFrame:
    """Fetch price data, trying DataStore first then YFinance connector.

    Parameters
    ----------
    ticker:
        Ticker symbol (e.g. "AAPL").
    start:
        Start date as ISO string (YYYY-MM-DD).
    end:
        End date as ISO string (YYYY-MM-DD).

    Returns
    -------
    pl.DataFrame
        OHLCV DataFrame with at minimum: date, open, high, low, close, volume.

    Raises
    ------
    ValueError
        If no stored data exists and the YFinance fallback also fails.
    """
    from data.storage.store import DataStore

    store = DataStore()
    prices = store.load_ohlcv(ticker, start, end)

    if prices.is_empty():
        # Try fetching from YFinance
        from core.connectors import ConnectorRegistry

        try:
            from data.fetchers.yfinance_connector import YFinanceConnector
            from datetime import date as d

            connector = YFinanceConnector()
            prices = connector.fetch_ohlcv(
                ticker,
                d.fromisoformat(start),
                d.fromisoformat(end),
            )
            store.save_ohlcv(ticker, prices, source="yfinance")
        except Exception as e:
            raise ValueError(
                f"No data for {ticker} and failed to fetch: {e}"
            ) from e

    return prices


def prepare_signals_for_backtest(
    signals: list,
    prices: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Prepare signals and prices for the backtest engine.

    Ensures:
    - signals is a DataFrame with [date, ticker, direction, confidence]
    - prices has [date, ticker, close] minimum
    - date types are aligned

    Parameters
    ----------
    signals:
        List of Signal objects.
    prices:
        OHLCV price DataFrame.

    Returns
    -------
    tuple[pl.DataFrame, pl.DataFrame]
        (signals_df, prices) with normalised date columns and ticker alignment.
    """
    from core.serialization import signals_to_dataframe
    from core.utils import normalize_date_column

    signals_df = signals_to_dataframe(signals)
    signals_df = normalize_date_column(signals_df)
    prices = normalize_date_column(prices)

    # Ensure ticker column in prices
    if "ticker" not in prices.columns:
        tickers = signals_df["ticker"].unique().to_list()
        if len(tickers) == 1:
            prices = prices.with_columns(pl.lit(tickers[0]).alias("ticker"))

    return signals_df, prices
