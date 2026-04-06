"""FRED (Federal Reserve Economic Data) connector for macroeconomic time series.

Provides production-grade access to the full FRED database via the fredapi
package. Designed for quantitative research workflows with Polars DataFrames,
automatic rate limiting, retry logic, and pre-defined constants for the most
commonly used macro indicators.

Usage:
    from data.fetchers.fred_connector import FREDConnector

    fred = FREDConnector()
    fred.connect()

    # Single series
    df = fred.fetch_series("DGS10", start=date(2020, 1, 1))

    # Multiple series aligned on date
    df = fred.fetch_multiple_series(
        [FREDSeries.FED_FUNDS, FREDSeries.DGS10, FREDSeries.DGS2],
        start=date(2020, 1, 1),
    )

    # Yield curve snapshot
    curve = fred.fetch_yield_curve(date(2024, 3, 15))

    # NBER recession bands
    recessions = fred.get_recession_dates()
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from functools import wraps
from typing import Any, Final

import polars as pl

from core.connectors import BaseConnector, ConnectorRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FRED_RATE_LIMIT_PER_MINUTE: Final[int] = 120
_DEFAULT_RETRY_ATTEMPTS: Final[int] = 3
_RETRY_BACKOFF_BASE: Final[float] = 1.0  # seconds; exponential backoff multiplier


class FREDSeries(StrEnum):
    """Pre-defined FRED series IDs for common macro indicators.

    Organized by category for discoverability. Each member's *value* is the
    canonical FRED series ID string so it can be passed directly to any method
    that accepts a ``series_id`` parameter.
    """

    # -- Interest Rates ------------------------------------------------------
    FED_FUNDS: str = "DFF"
    """Effective Federal Funds Rate (daily)."""

    DGS10: str = "DGS10"
    """Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity."""

    DGS2: str = "DGS2"
    """Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity."""

    YIELD_CURVE_SPREAD: str = "T10Y2Y"
    """10-Year minus 2-Year Treasury Constant Maturity spread."""

    DGS30: str = "DGS30"
    """30-Year Treasury Constant Maturity Rate."""

    DGS5: str = "DGS5"
    """5-Year Treasury Constant Maturity Rate."""

    DGS1: str = "DGS1"
    """1-Year Treasury Constant Maturity Rate."""

    DGS3MO: str = "DGS3MO"
    """3-Month Treasury Constant Maturity Rate."""

    # -- Economic Indicators -------------------------------------------------
    GDP: str = "GDP"
    """Gross Domestic Product (quarterly, seasonally adjusted annual rate)."""

    REAL_GDP: str = "GDPC1"
    """Real Gross Domestic Product (quarterly, chained 2017 dollars)."""

    UNRATE: str = "UNRATE"
    """Civilian Unemployment Rate (monthly, seasonally adjusted)."""

    CPI: str = "CPIAUCSL"
    """Consumer Price Index for All Urban Consumers (monthly, SA)."""

    CORE_CPI: str = "CPILFESL"
    """CPI Less Food and Energy (monthly, SA)."""

    PCE: str = "PCEPI"
    """Personal Consumption Expenditures Price Index (monthly)."""

    CORE_PCE: str = "PCEPILFE"
    """PCE Excluding Food and Energy (monthly)."""

    PAYROLLS: str = "PAYEMS"
    """All Employees: Total Nonfarm (monthly, SA)."""

    INITIAL_CLAIMS: str = "ICSA"
    """Initial Claims (weekly, SA)."""

    ISM_MANUFACTURING: str = "MANEMP"
    """ISM Manufacturing Employment Index."""

    RETAIL_SALES: str = "RSAFS"
    """Advance Retail Sales: Retail and Food Services (monthly)."""

    INDUSTRIAL_PRODUCTION: str = "INDPRO"
    """Industrial Production: Total Index (monthly, SA)."""

    # -- Financial / Markets -------------------------------------------------
    VIX: str = "VIXCLS"
    """CBOE Volatility Index (daily)."""

    HY_SPREAD: str = "BAMLH0A0HYM2"
    """ICE BofA US High Yield Index Option-Adjusted Spread (daily)."""

    IG_SPREAD: str = "BAMLC0A0CM"
    """ICE BofA US Corporate Index Option-Adjusted Spread (daily)."""

    USD_INDEX: str = "DTWEXBGS"
    """Nominal Broad U.S. Dollar Index (daily)."""

    SP500: str = "SP500"
    """S&P 500 Index (daily)."""

    M2: str = "M2SL"
    """M2 Money Stock (monthly, SA)."""

    # -- Housing -------------------------------------------------------------
    MORTGAGE_30Y: str = "MORTGAGE30US"
    """30-Year Fixed Rate Mortgage Average (weekly)."""

    CASE_SHILLER: str = "CSUSHPISA"
    """S&P/Case-Shiller U.S. National Home Price Index (monthly, SA)."""

    HOUSING_STARTS: str = "HOUST"
    """Housing Starts: Total (monthly, SAAR)."""

    # -- Recession Indicator -------------------------------------------------
    RECESSION: str = "USREC"
    """NBER-based Recession Indicator (1 = recession, 0 = expansion)."""


# Yield curve tenor series in order of maturity.
_YIELD_CURVE_TENORS: Final[dict[str, str]] = {
    "1M": "DGS1MO",
    "3M": "DGS3MO",
    "6M": "DGS6MO",
    "1Y": "DGS1",
    "2Y": "DGS2",
    "3Y": "DGS3",
    "5Y": "DGS5",
    "7Y": "DGS7",
    "10Y": "DGS10",
    "20Y": "DGS20",
    "30Y": "DGS30",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FREDConnectorError(Exception):
    """Base exception for all FRED connector errors."""


class FREDAuthenticationError(FREDConnectorError):
    """Raised when the FRED API key is missing or invalid."""


class FREDRateLimitError(FREDConnectorError):
    """Raised when the FRED rate limit is exceeded and retries are exhausted."""


class FREDDataError(FREDConnectorError):
    """Raised when FRED returns unexpected or invalid data."""


# ---------------------------------------------------------------------------
# Rate limiter (token-bucket)
# ---------------------------------------------------------------------------


@dataclass
class _TokenBucketRateLimiter:
    """Thread-safe token-bucket rate limiter.

    Parameters
    ----------
    rate : int
        Maximum number of requests per ``per`` seconds.
    per : float
        Time window in seconds (default 60 for per-minute limits).
    """

    rate: int = _FRED_RATE_LIMIT_PER_MINUTE
    per: float = 60.0
    _tokens: float = field(init=False, default=0.0)
    _last_refill: float = field(init=False, default_factory=time.monotonic)
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self._tokens = float(self.rate)

    def acquire(self) -> None:
        """Block until a token is available, then consume one."""
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(
                    float(self.rate),
                    self._tokens + elapsed * (self.rate / self.per),
                )
                self._last_refill = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            # Sleep briefly outside the lock to avoid busy-waiting.
            time.sleep(0.05)


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------


def _retry_with_backoff(
    max_attempts: int = _DEFAULT_RETRY_ATTEMPTS,
    backoff_base: float = _RETRY_BACKOFF_BASE,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """Decorator: retry a function with exponential backoff on failure.

    Parameters
    ----------
    max_attempts : int
        Total number of attempts (including the first).
    backoff_base : float
        Base sleep duration in seconds. Actual sleep is
        ``backoff_base * 2 ** (attempt - 1)``.
    retryable_exceptions : tuple
        Exception types that trigger a retry. All others propagate immediately.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    sleep_secs = backoff_base * (2 ** (attempt - 1))
                    logger.warning(
                        "FRED request failed (attempt %d/%d): %s. "
                        "Retrying in %.1fs ...",
                        attempt,
                        max_attempts,
                        exc,
                        sleep_secs,
                    )
                    time.sleep(sleep_secs)
            raise FREDConnectorError(
                f"FRED request failed after {max_attempts} attempts"
            ) from last_exc

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# BaseMacroDataConnector (new abstract interface)
# ---------------------------------------------------------------------------


class BaseMacroDataConnector(BaseConnector):
    """Interface for macroeconomic / fundamental time-series data sources.

    Subclass this for FRED, BLS, BEA, ECB, or any provider whose primary
    output is date-indexed scalar time series rather than OHLCV bars.
    """

    from abc import abstractmethod

    @abstractmethod
    def fetch_series(
        self,
        series_id: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Fetch a single time series.

        Returns a DataFrame with columns ``["date", "value"]``.
        """

    @abstractmethod
    def fetch_multiple_series(
        self,
        series_ids: list[str],
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Fetch multiple series aligned by date.

        Returns a DataFrame with a ``"date"`` column and one additional column
        per series named by its series ID.
        """


# ---------------------------------------------------------------------------
# FRED Connector
# ---------------------------------------------------------------------------


class FREDConnector(BaseMacroDataConnector):
    """Production-grade FRED connector for quantitative macro research.

    Features
    --------
    * Full ``fredapi`` integration with automatic Polars conversion.
    * Token-bucket rate limiter honouring FRED's 120 req/min cap.
    * Exponential-backoff retry on transient network / server errors.
    * Pre-defined ``FREDSeries`` enum for common indicators.
    * Yield-curve snapshot and NBER recession-date convenience methods.
    * Graceful error handling -- no silent failures.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        rate_limit: int = _FRED_RATE_LIMIT_PER_MINUTE,
        max_retries: int = _DEFAULT_RETRY_ATTEMPTS,
    ) -> None:
        self._api_key: str | None = api_key
        self._fred: Any = None  # fredapi.Fred instance; lazily initialised
        self._rate_limiter = _TokenBucketRateLimiter(rate=rate_limit)
        self._max_retries = max_retries
        self._connected: bool = False

    # -- BaseConnector interface --------------------------------------------

    @property
    def name(self) -> str:  # noqa: D401
        return "FRED"

    def connect(self) -> None:
        """Resolve the API key and instantiate the fredapi client.

        Raises
        ------
        FREDAuthenticationError
            If no API key is found in the constructor argument *or* the
            ``FRED_API_KEY`` environment variable.
        """
        try:
            from fredapi import Fred  # type: ignore[import-untyped]
        except ImportError as exc:
            raise FREDConnectorError(
                "The 'fredapi' package is required but not installed. "
                "Install it with:  pip install fredapi  (or  uv add fredapi)"
            ) from exc

        resolved_key = self._api_key or os.environ.get("FRED_API_KEY")
        if not resolved_key:
            raise FREDAuthenticationError(
                "FRED API key not found. Either pass api_key= to FREDConnector "
                "or set the FRED_API_KEY environment variable.\n"
                "  Register for a free key at: https://fred.stlouisfed.org/docs/api/api_key.html"
            )

        self._fred = Fred(api_key=resolved_key)
        self._connected = True
        logger.info("FRED connector initialised successfully.")

    def health_check(self) -> bool:
        """Validate connectivity by fetching a tiny slice of the fed-funds rate."""
        if not self._connected or self._fred is None:
            return False
        try:
            self._rate_limiter.acquire()
            result = self._fred.get_series(
                "DFF",
                observation_start="2024-01-02",
                observation_end="2024-01-02",
            )
            return result is not None and len(result) > 0
        except Exception:
            logger.exception("FRED health-check failed.")
            return False

    # -- Internal helpers ---------------------------------------------------

    def _ensure_connected(self) -> None:
        """Raise if ``connect()`` has not been called successfully."""
        if not self._connected or self._fred is None:
            raise FREDConnectorError(
                "FREDConnector is not connected. Call connect() first."
            )

    def _fetch_raw_series(
        self,
        series_id: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Low-level fetch: rate-limited, retried, returns a Polars DataFrame.

        The returned DataFrame always has exactly two columns:
        ``["date", "value"]`` where ``date`` is ``pl.Date`` and ``value`` is
        ``pl.Float64``.  Missing observations (FRED uses ``.`` for N/A) are
        dropped.
        """
        import pandas as pd  # local import -- only needed here

        self._ensure_connected()

        obs_start = start.isoformat() if start else None
        obs_end = end.isoformat() if end else None

        @_retry_with_backoff(
            max_attempts=self._max_retries,
            retryable_exceptions=(Exception,),
        )
        def _do_fetch() -> pd.Series:
            self._rate_limiter.acquire()
            return self._fred.get_series(
                series_id,
                observation_start=obs_start,
                observation_end=obs_end,
            )

        try:
            raw: pd.Series = _do_fetch()
        except FREDConnectorError:
            raise
        except Exception as exc:
            raise FREDDataError(
                f"Failed to fetch FRED series '{series_id}': {exc}"
            ) from exc

        if raw is None or raw.empty:
            logger.warning("FRED series '%s' returned no observations.", series_id)
            return pl.DataFrame(
                {"date": pl.Series([], dtype=pl.Date), "value": pl.Series([], dtype=pl.Float64)}
            )

        # Convert pandas Series -> Polars DataFrame, clean NaN / missing.
        pdf = raw.reset_index()
        pdf.columns = ["date", "value"]

        df = pl.from_pandas(pdf).with_columns(
            pl.col("date").cast(pl.Date),
            pl.col("value").cast(pl.Float64, strict=False),
        ).drop_nulls(subset=["value"])

        return df

    # -- Public data methods ------------------------------------------------

    def fetch_series(
        self,
        series_id: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Fetch a single FRED time series.

        Parameters
        ----------
        series_id : str
            FRED series identifier (e.g. ``"DGS10"``) or a ``FREDSeries`` enum
            member.
        start : date, optional
            Earliest observation date (inclusive). ``None`` means "as far back
            as FRED has data".
        end : date, optional
            Latest observation date (inclusive). ``None`` means today.

        Returns
        -------
        pl.DataFrame
            Columns: ``["date", "value"]``.
        """
        sid = str(series_id)
        logger.debug("Fetching FRED series: %s", sid)
        return self._fetch_raw_series(sid, start=start, end=end)

    def fetch_multiple_series(
        self,
        series_ids: list[str],
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Fetch multiple FRED series and join them on date.

        Parameters
        ----------
        series_ids : list[str]
            List of FRED series identifiers.
        start : date, optional
            Earliest observation date.
        end : date, optional
            Latest observation date.

        Returns
        -------
        pl.DataFrame
            One ``"date"`` column plus one ``pl.Float64`` column per series,
            named by its series ID. An outer join is used so that series with
            different frequencies still align; missing values appear as
            ``null``.
        """
        if not series_ids:
            raise ValueError("series_ids must be a non-empty list.")

        frames: dict[str, pl.DataFrame] = {}
        for sid in series_ids:
            sid = str(sid)
            df = self._fetch_raw_series(sid, start=start, end=end)
            frames[sid] = df.rename({"value": sid})

        # Progressive outer-join to keep all dates.
        ids = list(frames.keys())
        result = frames[ids[0]]
        for sid in ids[1:]:
            result = result.join(frames[sid], on="date", how="full", coalesce=True)

        # Sort chronologically.
        result = result.sort("date")
        return result

    def fetch_yield_curve(
        self,
        as_of: date | None = None,
    ) -> pl.DataFrame:
        """Fetch the U.S. Treasury yield curve for a specific date.

        Parameters
        ----------
        as_of : date, optional
            The observation date. Defaults to the most recent available date.

        Returns
        -------
        pl.DataFrame
            Columns: ``["tenor", "maturity_years", "yield_pct"]``.
            ``maturity_years`` is a float for sorting / interpolation.
        """
        self._ensure_connected()

        tenor_labels: list[str] = []
        maturity_years: list[float] = []
        yields: list[float | None] = []

        _tenor_to_years: dict[str, float] = {
            "1M": 1 / 12,
            "3M": 0.25,
            "6M": 0.5,
            "1Y": 1.0,
            "2Y": 2.0,
            "3Y": 3.0,
            "5Y": 5.0,
            "7Y": 7.0,
            "10Y": 10.0,
            "20Y": 20.0,
            "30Y": 30.0,
        }

        # Determine the date window: if as_of is provided use that single day,
        # otherwise pull the last 5 business days and take the most recent.
        if as_of is not None:
            window_start = as_of
            window_end = as_of
        else:
            window_end = date.today()
            # Go back ~10 calendar days to be safe across weekends / holidays.
            window_start = date(
                window_end.year,
                window_end.month,
                max(window_end.day - 10, 1),
            )
            # Handle month boundary with timedelta for correctness.
            from datetime import timedelta

            window_start = window_end - timedelta(days=10)

        for tenor, fred_id in _YIELD_CURVE_TENORS.items():
            df = self._fetch_raw_series(fred_id, start=window_start, end=window_end)

            if df.is_empty():
                tenor_labels.append(tenor)
                maturity_years.append(_tenor_to_years[tenor])
                yields.append(None)
                continue

            # Take the most recent observation.
            last_row = df.sort("date").tail(1)
            tenor_labels.append(tenor)
            maturity_years.append(_tenor_to_years[tenor])
            yields.append(last_row["value"][0])

        curve_df = pl.DataFrame(
            {
                "tenor": tenor_labels,
                "maturity_years": maturity_years,
                "yield_pct": yields,
            },
            schema={
                "tenor": pl.Utf8,
                "maturity_years": pl.Float64,
                "yield_pct": pl.Float64,
            },
        ).drop_nulls(subset=["yield_pct"])

        return curve_df

    def get_recession_dates(self) -> pl.DataFrame:
        """Return NBER recession start and end dates.

        Uses the ``USREC`` binary indicator (1 = recession month) and
        computes contiguous recession bands.

        Returns
        -------
        pl.DataFrame
            Columns: ``["start", "end"]`` (both ``pl.Date``).  Each row is
            one recession episode.
        """
        df = self.fetch_series(FREDSeries.RECESSION)

        if df.is_empty():
            return pl.DataFrame(
                {"start": pl.Series([], dtype=pl.Date), "end": pl.Series([], dtype=pl.Date)}
            )

        # Identify transitions: 0->1 = recession start, 1->0 = recession end.
        df = df.sort("date").with_columns(
            pl.col("value").cast(pl.Int8).alias("recession"),
        ).with_columns(
            pl.col("recession").shift(1).fill_null(0).alias("prev"),
        )

        starts = df.filter(
            (pl.col("recession") == 1) & (pl.col("prev") == 0)
        ).select(pl.col("date").alias("start"))

        ends = df.filter(
            (pl.col("recession") == 0) & (pl.col("prev") == 1)
        ).select(pl.col("date").alias("end"))

        # If currently in a recession the last start has no matching end.
        # Pad ends with today's date so the frames align.
        if starts.height > ends.height:
            ends = pl.concat([
                ends,
                pl.DataFrame({"end": [date.today()]}, schema={"end": pl.Date}),
            ])

        recessions = pl.concat([starts, ends], how="horizontal")
        return recessions

    def get_series_info(self, series_id: str) -> dict[str, Any]:
        """Return FRED metadata for a series (title, frequency, units, etc.).

        Parameters
        ----------
        series_id : str
            FRED series identifier.

        Returns
        -------
        dict[str, Any]
            Raw metadata dictionary from the FRED API.
        """
        self._ensure_connected()
        self._rate_limiter.acquire()

        @_retry_with_backoff(max_attempts=self._max_retries)
        def _do_fetch() -> dict[str, Any]:
            info = self._fred.get_series_info(str(series_id))
            return info.to_dict()

        return _do_fetch()

    def search_series(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> pl.DataFrame:
        """Search FRED for series matching a text query.

        Parameters
        ----------
        query : str
            Free-text search string.
        limit : int
            Maximum number of results to return.

        Returns
        -------
        pl.DataFrame
            Columns include ``["id", "title", "frequency", "units",
            "seasonal_adjustment"]``.
        """
        self._ensure_connected()
        self._rate_limiter.acquire()

        @_retry_with_backoff(max_attempts=self._max_retries)
        def _do_search():
            return self._fred.search(query, limit=limit)

        results_pdf = _do_search()

        if results_pdf is None or results_pdf.empty:
            return pl.DataFrame(
                schema={
                    "id": pl.Utf8,
                    "title": pl.Utf8,
                    "frequency": pl.Utf8,
                    "units": pl.Utf8,
                    "seasonal_adjustment": pl.Utf8,
                }
            )

        results_pdf = results_pdf.reset_index()

        keep_cols = [
            c
            for c in ["id", "title", "frequency", "units", "seasonal_adjustment"]
            if c in results_pdf.columns
        ]
        return pl.from_pandas(results_pdf[keep_cols])

    # -- Convenience shortcuts ----------------------------------------------

    def fetch_interest_rates(
        self,
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Convenience: fetch the core interest-rate series in one call."""
        return self.fetch_multiple_series(
            [
                FREDSeries.FED_FUNDS,
                FREDSeries.DGS2,
                FREDSeries.DGS5,
                FREDSeries.DGS10,
                FREDSeries.DGS30,
                FREDSeries.YIELD_CURVE_SPREAD,
            ],
            start=start,
            end=end,
        )

    def fetch_inflation_indicators(
        self,
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Convenience: fetch headline and core CPI / PCE series."""
        return self.fetch_multiple_series(
            [
                FREDSeries.CPI,
                FREDSeries.CORE_CPI,
                FREDSeries.PCE,
                FREDSeries.CORE_PCE,
            ],
            start=start,
            end=end,
        )

    def fetch_labor_market(
        self,
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Convenience: fetch unemployment, payrolls, and initial claims."""
        return self.fetch_multiple_series(
            [
                FREDSeries.UNRATE,
                FREDSeries.PAYROLLS,
                FREDSeries.INITIAL_CLAIMS,
            ],
            start=start,
            end=end,
        )

    def fetch_financial_conditions(
        self,
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Convenience: fetch VIX, credit spreads, and USD index."""
        return self.fetch_multiple_series(
            [
                FREDSeries.VIX,
                FREDSeries.HY_SPREAD,
                FREDSeries.IG_SPREAD,
                FREDSeries.USD_INDEX,
            ],
            start=start,
            end=end,
        )

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return f"FREDConnector(status={status})"


# ---------------------------------------------------------------------------
# Register with the connector registry
# ---------------------------------------------------------------------------

ConnectorRegistry.register("fred", FREDConnector)
