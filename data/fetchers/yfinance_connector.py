"""YFinance connector for fetching market data via the yfinance library.

Implements BaseMarketDataConnector with rate limiting, retry logic,
and automatic pandas-to-polars conversion.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from datetime import date, datetime
from typing import Any

import polars as pl
import yfinance as yf

from core.connectors import BaseMarketDataConnector, ConnectorRegistry

logger = logging.getLogger(__name__)

_VALID_INTERVALS = ("1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo")

# yfinance caps intraday history windows depending on interval
_MAX_INTRADAY_DAYS: dict[str, int] = {
    "1m": 7,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "1h": 730,
}

_OHLCV_COLUMN_MAP: dict[str, str] = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
    "Adj Close": "adj_close",
}


class YFinanceError(Exception):
    """Base exception for YFinance connector errors."""


class TickerNotFoundError(YFinanceError):
    """Raised when a ticker symbol cannot be resolved."""


class NoDataError(YFinanceError):
    """Raised when yfinance returns an empty dataset."""


class RateLimitError(YFinanceError):
    """Raised when the rate limiter rejects a request."""


class _RateLimiter:
    """Sliding-window rate limiter. Thread-safe."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max_requests = max_requests
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> None:
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                now = time.monotonic()
                while self._timestamps and self._timestamps[0] <= now - self._window:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._max_requests:
                    self._timestamps.append(now)
                    return
                wait = self._timestamps[0] + self._window - now
            if time.monotonic() + wait > deadline:
                raise RateLimitError(
                    f"Rate limit timeout: could not acquire slot within {timeout}s"
                )
            time.sleep(min(wait, 0.5))


def _retry_with_backoff(
    fn: Any,
    *args: Any,
    retries: int = 3,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> Any:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = base_delay * (2**attempt)
                logger.warning(
                    "Attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt + 1,
                    retries,
                    exc,
                    delay,
                )
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


def _validate_interval(interval: str) -> None:
    if interval not in _VALID_INTERVALS:
        raise ValueError(
            f"Invalid interval '{interval}'. Must be one of: {', '.join(_VALID_INTERVALS)}"
        )


def _pandas_ohlcv_to_polars(pdf: Any, ticker: str) -> pl.DataFrame:
    """Convert a yfinance pandas OHLCV DataFrame to a normalized polars DataFrame."""
    if pdf is None or pdf.empty:
        raise NoDataError(f"No OHLCV data returned for '{ticker}'")

    pdf = pdf.reset_index()

    # yfinance names the index column "Date" for daily or "Datetime" for intraday
    date_col = "Date" if "Date" in pdf.columns else "Datetime"
    pdf = pdf.rename(columns={date_col: "date", **_OHLCV_COLUMN_MAP})

    keep = [c for c in ("date", "open", "high", "low", "close", "volume", "adj_close") if c in pdf.columns]
    pdf = pdf[keep]

    df = pl.from_pandas(pdf)

    # Ensure date column is proper datetime, stripping timezone if present
    if df.schema["date"] in (pl.Datetime, pl.Date):
        pass
    else:
        df = df.with_columns(pl.col("date").cast(pl.Datetime))

    if df.schema["date"] == pl.Datetime("ns", "UTC") or (
        isinstance(df.schema["date"], pl.Datetime) and df.schema["date"].time_zone is not None  # type: ignore[union-attr]
    ):
        df = df.with_columns(pl.col("date").dt.replace_time_zone(None))

    return df


class YFinanceConnector(BaseMarketDataConnector):
    """Production-grade YFinance market data connector.

    Parameters
    ----------
    max_requests_per_hour:
        Cap on requests within a rolling hour window. yfinance's unofficial
        limit is ~2000/hour; default is conservative at 1800.
    retries:
        Number of retry attempts per request.
    base_delay:
        Base delay in seconds for exponential backoff.
    """

    def __init__(
        self,
        max_requests_per_hour: int = 1800,
        retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        self._retries = retries
        self._base_delay = base_delay
        self._limiter = _RateLimiter(
            max_requests=max_requests_per_hour,
            window_seconds=3600.0,
        )
        self._connected = False

    # ------------------------------------------------------------------
    # BaseConnector interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "yfinance"

    def connect(self) -> None:
        logger.info("YFinanceConnector: validating connectivity")
        try:
            test = yf.Ticker("AAPL")
            hist = test.history(period="1d")
            if hist is None or hist.empty:
                raise YFinanceError("Connectivity check returned no data")
        except Exception as exc:
            logger.error("YFinanceConnector: connectivity check failed: %s", exc)
            raise
        self._connected = True
        logger.info("YFinanceConnector: connected")

    def health_check(self) -> bool:
        try:
            test = yf.Ticker("AAPL")
            hist = test.history(period="1d")
            return hist is not None and not hist.empty
        except Exception:
            return False

    # ------------------------------------------------------------------
    # BaseMarketDataConnector interface
    # ------------------------------------------------------------------

    def fetch_ohlcv(
        self,
        ticker: str,
        start: date,
        end: date,
        interval: str = "1d",
    ) -> pl.DataFrame:
        _validate_interval(interval)
        self._limiter.acquire()

        start_str = start.isoformat()
        end_str = end.isoformat()

        logger.debug(
            "Fetching OHLCV: ticker=%s start=%s end=%s interval=%s",
            ticker,
            start_str,
            end_str,
            interval,
        )

        def _download() -> Any:
            t = yf.Ticker(ticker)
            pdf = t.history(start=start_str, end=end_str, interval=interval, auto_adjust=False)
            return pdf

        pdf = _retry_with_backoff(
            _download, retries=self._retries, base_delay=self._base_delay
        )

        try:
            return _pandas_ohlcv_to_polars(pdf, ticker)
        except NoDataError:
            raise
        except Exception as exc:
            raise YFinanceError(f"Failed to process data for '{ticker}': {exc}") from exc

    def fetch_multiple(
        self,
        tickers: list[str],
        start: date,
        end: date,
        interval: str = "1d",
    ) -> dict[str, pl.DataFrame]:
        _validate_interval(interval)

        if not tickers:
            return {}

        self._limiter.acquire()

        start_str = start.isoformat()
        end_str = end.isoformat()
        space_joined = " ".join(tickers)

        logger.debug(
            "Batch fetching OHLCV: tickers=%s start=%s end=%s interval=%s",
            space_joined,
            start_str,
            end_str,
            interval,
        )

        def _batch_download() -> Any:
            return yf.download(
                space_joined,
                start=start_str,
                end=end_str,
                interval=interval,
                auto_adjust=False,
                group_by="ticker",
                threads=True,
            )

        raw = _retry_with_backoff(
            _batch_download, retries=self._retries, base_delay=self._base_delay
        )

        results: dict[str, pl.DataFrame] = {}

        if len(tickers) == 1:
            # yf.download returns a flat DataFrame for a single ticker
            try:
                results[tickers[0]] = _pandas_ohlcv_to_polars(raw, tickers[0])
            except NoDataError:
                logger.warning("No data for '%s', skipping", tickers[0])
            return results

        # Multi-ticker: columns are a MultiIndex (ticker, field)
        for ticker in tickers:
            try:
                if ticker not in raw.columns.get_level_values(0):
                    logger.warning("Ticker '%s' not found in batch result", ticker)
                    continue
                ticker_pdf = raw[ticker].copy()
                results[ticker] = _pandas_ohlcv_to_polars(ticker_pdf, ticker)
            except (NoDataError, KeyError):
                logger.warning("No data for '%s', skipping", ticker)
            except Exception as exc:
                logger.error("Error processing '%s': %s", ticker, exc)

        return results

    def supported_intervals(self) -> list[str]:
        return list(_VALID_INTERVALS)

    # ------------------------------------------------------------------
    # Extended methods
    # ------------------------------------------------------------------

    def fetch_info(self, ticker: str) -> dict[str, Any]:
        """Fetch ticker metadata (market cap, sector, industry, etc.)."""
        self._limiter.acquire()

        def _get_info() -> dict[str, Any]:
            t = yf.Ticker(ticker)
            info: dict[str, Any] = t.info
            if not info or info.get("regularMarketPrice") is None:
                raise TickerNotFoundError(
                    f"Ticker '{ticker}' not found or has no market data"
                )
            return info

        return _retry_with_backoff(
            _get_info, retries=self._retries, base_delay=self._base_delay
        )

    def fetch_dividends(self, ticker: str, start: date | None = None, end: date | None = None) -> pl.DataFrame:
        """Fetch dividend history. Returns columns: date, dividends."""
        self._limiter.acquire()

        def _get_dividends() -> Any:
            t = yf.Ticker(ticker)
            return t.dividends

        series = _retry_with_backoff(
            _get_dividends, retries=self._retries, base_delay=self._base_delay
        )

        if series is None or series.empty:
            return pl.DataFrame(schema={"date": pl.Datetime, "dividends": pl.Float64})

        pdf = series.reset_index()
        pdf.columns = ["date", "dividends"]
        df = pl.from_pandas(pdf)

        if isinstance(df.schema["date"], pl.Datetime) and df.schema["date"].time_zone is not None:  # type: ignore[union-attr]
            df = df.with_columns(pl.col("date").dt.replace_time_zone(None))

        if start is not None:
            df = df.filter(pl.col("date") >= datetime(start.year, start.month, start.day))
        if end is not None:
            df = df.filter(pl.col("date") <= datetime(end.year, end.month, end.day))

        return df

    def fetch_splits(self, ticker: str, start: date | None = None, end: date | None = None) -> pl.DataFrame:
        """Fetch stock split history. Returns columns: date, stock_splits."""
        self._limiter.acquire()

        def _get_splits() -> Any:
            t = yf.Ticker(ticker)
            return t.splits

        series = _retry_with_backoff(
            _get_splits, retries=self._retries, base_delay=self._base_delay
        )

        if series is None or series.empty:
            return pl.DataFrame(schema={"date": pl.Datetime, "stock_splits": pl.Float64})

        pdf = series.reset_index()
        pdf.columns = ["date", "stock_splits"]
        df = pl.from_pandas(pdf)

        if isinstance(df.schema["date"], pl.Datetime) and df.schema["date"].time_zone is not None:  # type: ignore[union-attr]
            df = df.with_columns(pl.col("date").dt.replace_time_zone(None))

        if start is not None:
            df = df.filter(pl.col("date") >= datetime(start.year, start.month, start.day))
        if end is not None:
            df = df.filter(pl.col("date") <= datetime(end.year, end.month, end.day))

        return df


ConnectorRegistry.register("yfinance", YFinanceConnector)
