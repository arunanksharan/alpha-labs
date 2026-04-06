"""SEC EDGAR connector for fetching filings, financial statements, and XBRL data.

Uses SEC EDGAR's free REST API. No API key required -- only a compliant
User-Agent header identifying the caller (per SEC fair-access policy).

Rate limit: hard cap of 10 requests/second enforced via a token-bucket
rate limiter. SEC will throttle or ban clients that exceed this.

Example usage:
    connector = EdgarConnector()
    connector.connect()
    facts = connector.fetch_company_facts("AAPL")
    filings = connector.fetch_filings("AAPL", "10-K", date(2020, 1, 1), date(2024, 1, 1))
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

import httpx
import polars as pl

from core.connectors import BaseFundamentalConnector, ConnectorRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SEC_BASE = "https://www.sec.gov"
_SEC_DATA = "https://data.sec.gov"
_SEC_EFTS = "https://efts.sec.gov/LATEST"

_USER_AGENT = "QuantResearcher research@kuzushilabs.com"

_MAX_REQUESTS_PER_SECOND = 10

# XBRL taxonomy -> human-readable name mappings for the most common US-GAAP
# concepts we pull from company facts.
_INCOME_CONCEPTS: dict[str, str] = {
    "Revenues": "revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "SalesRevenueNet": "revenue",
    "CostOfGoodsAndServicesSold": "cost_of_revenue",
    "CostOfRevenue": "cost_of_revenue",
    "CostOfGoodsSold": "cost_of_revenue",
    "GrossProfit": "gross_profit",
    "OperatingExpenses": "operating_expenses",
    "OperatingIncomeLoss": "operating_income",
    "NetIncomeLoss": "net_income",
    "EarningsPerShareBasic": "eps_basic",
    "EarningsPerShareDiluted": "eps_diluted",
    "ResearchAndDevelopmentExpense": "research_and_development",
    "SellingGeneralAndAdministrativeExpense": "sga",
    "InterestExpense": "interest_expense",
    "IncomeTaxExpenseBenefit": "income_tax",
    "DepreciationDepletionAndAmortization": "depreciation_amortization",
}

_BALANCE_CONCEPTS: dict[str, str] = {
    "Assets": "total_assets",
    "AssetsCurrent": "current_assets",
    "Liabilities": "total_liabilities",
    "LiabilitiesCurrent": "current_liabilities",
    "StockholdersEquity": "total_equity",
    "CashAndCashEquivalentsAtCarryingValue": "cash_and_equivalents",
    "ShortTermInvestments": "short_term_investments",
    "AccountsReceivableNetCurrent": "accounts_receivable",
    "InventoryNet": "inventory",
    "PropertyPlantAndEquipmentNet": "property_plant_equipment",
    "Goodwill": "goodwill",
    "LongTermDebt": "long_term_debt",
    "LongTermDebtNoncurrent": "long_term_debt",
    "ShortTermBorrowings": "short_term_debt",
    "CommonStockSharesOutstanding": "shares_outstanding",
    "RetainedEarningsAccumulatedDeficit": "retained_earnings",
}

_CASHFLOW_CONCEPTS: dict[str, str] = {
    "NetCashProvidedByUsedInOperatingActivities": "operating_cash_flow",
    "NetCashProvidedByUsedInInvestingActivities": "investing_cash_flow",
    "NetCashProvidedByUsedInFinancingActivities": "financing_cash_flow",
    "PaymentsToAcquirePropertyPlantAndEquipment": "capital_expenditures",
    "PaymentsOfDividends": "dividends_paid",
    "PaymentsForRepurchaseOfCommonStock": "share_repurchases",
    "DepreciationDepletionAndAmortization": "depreciation_amortization",
}

_STATEMENT_CONCEPTS: dict[str, dict[str, str]] = {
    "income": _INCOME_CONCEPTS,
    "balance": _BALANCE_CONCEPTS,
    "cashflow": _CASHFLOW_CONCEPTS,
}


class FilingType(str, Enum):
    """Supported SEC filing types."""

    ANNUAL = "10-K"
    QUARTERLY = "10-Q"
    CURRENT = "8-K"
    PROXY = "DEF 14A"
    REGISTRATION = "S-1"


_VALID_FILING_TYPES = {ft.value for ft in FilingType}


# ---------------------------------------------------------------------------
# Rate limiter (token bucket)
# ---------------------------------------------------------------------------


class _TokenBucketRateLimiter:
    """Thread-safe token-bucket rate limiter.

    Enforces a maximum of *rate* requests per second. Callers block on
    :meth:`acquire` until a token is available.
    """

    def __init__(self, rate: float = _MAX_REQUESTS_PER_SECOND) -> None:
        self._rate = rate
        self._tokens = rate
        self._max_tokens = rate
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a token is available, then consume one."""
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(
                    self._max_tokens,
                    self._tokens + elapsed * self._rate,
                )
                self._last_refill = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            # Sleep just enough so at least one token will be available.
            time.sleep(1.0 / self._rate)


# ---------------------------------------------------------------------------
# Dataclass for filing metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FilingMetadata:
    """Metadata for a single SEC filing."""

    accession_number: str
    filing_type: str
    filing_date: date
    primary_document: str
    description: str
    url: str
    cik: str


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class EdgarError(Exception):
    """Base exception for EDGAR connector errors."""


class CIKNotFoundError(EdgarError):
    """Raised when a ticker cannot be resolved to a CIK."""


class FilingNotFoundError(EdgarError):
    """Raised when a filing cannot be located."""


class RateLimitError(EdgarError):
    """Raised when SEC rate-limits us (HTTP 429)."""


# ---------------------------------------------------------------------------
# EdgarConnector
# ---------------------------------------------------------------------------


class EdgarConnector(BaseFundamentalConnector):
    """Production-grade SEC EDGAR connector.

    Provides access to SEC filings, structured XBRL financial data, and
    full-text search through EDGAR's free REST API.

    Parameters
    ----------
    user_agent:
        User-Agent string sent with every request.  SEC requires the format
        ``"Company/App contact@email.com"``.
    max_retries:
        Maximum number of retries on transient HTTP errors.
    backoff_factor:
        Multiplicative backoff factor between retries.
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        user_agent: str = _USER_AGENT,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        self._user_agent = user_agent
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._timeout = timeout

        self._client: httpx.Client | None = None
        self._rate_limiter = _TokenBucketRateLimiter()

        # In-memory CIK cache: ticker -> zero-padded 10-digit CIK string
        self._cik_cache: dict[str, str] = {}
        self._cik_cache_lock = threading.Lock()

        # Full company tickers map (loaded lazily on first CIK lookup)
        self._company_tickers: dict[str, dict[str, Any]] | None = None

    # ------------------------------------------------------------------
    # BaseConnector interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "sec_edgar"

    def connect(self) -> None:
        """Create the HTTP client with the required User-Agent header."""
        if self._client is not None:
            self._client.close()
        self._client = httpx.Client(
            headers={
                "User-Agent": self._user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=self._timeout,
            follow_redirects=True,
        )
        logger.info("EdgarConnector: HTTP client initialised (User-Agent=%s)", self._user_agent)

    def health_check(self) -> bool:
        """Verify we can reach SEC EDGAR."""
        try:
            resp = self._request("GET", f"{_SEC_DATA}/submissions/CIK0000320193.json")
            return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            self.connect()
        assert self._client is not None  # satisfy type checker
        return self._client

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Issue an HTTP request with rate limiting and retry/backoff.

        Retries on 429, 5xx, and transient connection errors.
        """
        client = self._ensure_client()
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            self._rate_limiter.acquire()
            try:
                resp = client.request(method, url, params=params)

                if resp.status_code == 429:
                    wait = self._backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        "SEC rate limited (429). Backing off %.1fs (attempt %d/%d)",
                        wait,
                        attempt,
                        self._max_retries,
                    )
                    time.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    wait = self._backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        "SEC server error %d. Retrying in %.1fs (attempt %d/%d)",
                        resp.status_code,
                        wait,
                        attempt,
                        self._max_retries,
                    )
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp

            except httpx.HTTPStatusError:
                raise
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.PoolTimeout) as exc:
                last_exc = exc
                wait = self._backoff_factor * (2 ** (attempt - 1))
                logger.warning(
                    "Transient error: %s. Retrying in %.1fs (attempt %d/%d)",
                    exc,
                    wait,
                    attempt,
                    self._max_retries,
                )
                time.sleep(wait)

        if last_exc is not None:
            raise EdgarError(f"Request failed after {self._max_retries} retries: {last_exc}") from last_exc
        raise EdgarError(f"Request failed after {self._max_retries} retries for {url}")

    def _get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        resp = self._request("GET", url, params=params)
        return resp.json()

    def _get_text(self, url: str) -> str:
        resp = self._request("GET", url)
        return resp.text

    # ------------------------------------------------------------------
    # CIK resolution
    # ------------------------------------------------------------------

    def _load_company_tickers(self) -> dict[str, dict[str, Any]]:
        """Load the SEC company tickers JSON (cached after first call)."""
        if self._company_tickers is not None:
            return self._company_tickers

        data = self._get_json(f"{_SEC_BASE}/files/company_tickers.json")
        # The response is a dict keyed by string index ("0", "1", ...),
        # each value: {"cik_str": int, "ticker": str, "title": str}
        self._company_tickers = data
        return data

    def _resolve_cik(self, ticker: str) -> str:
        """Resolve a ticker symbol to a zero-padded 10-digit CIK string.

        Results are cached in memory -- CIK mappings are stable.

        Raises
        ------
        CIKNotFoundError
            If the ticker cannot be found in SEC's company tickers file.
        """
        ticker_upper = ticker.upper().strip()

        with self._cik_cache_lock:
            if ticker_upper in self._cik_cache:
                return self._cik_cache[ticker_upper]

        tickers_data = self._load_company_tickers()

        for _idx, entry in tickers_data.items():
            if entry.get("ticker", "").upper() == ticker_upper:
                cik = str(entry["cik_str"]).zfill(10)
                with self._cik_cache_lock:
                    self._cik_cache[ticker_upper] = cik
                logger.debug("Resolved %s -> CIK %s", ticker_upper, cik)
                return cik

        raise CIKNotFoundError(
            f"Could not resolve ticker '{ticker}' to a CIK. "
            "Verify the ticker exists on SEC EDGAR."
        )

    # ------------------------------------------------------------------
    # Filing metadata
    # ------------------------------------------------------------------

    def fetch_filings(
        self,
        ticker: str,
        filing_type: str = "10-K",
        start: date | None = None,
        end: date | None = None,
    ) -> list[FilingMetadata]:
        """Fetch filing metadata for a company.

        Parameters
        ----------
        ticker:
            Stock ticker symbol (e.g. ``"AAPL"``).
        filing_type:
            SEC form type. Supported: 10-K, 10-Q, 8-K, DEF 14A, S-1.
        start / end:
            Optional date range filter for filing dates.

        Returns
        -------
        list[FilingMetadata]
            Filing metadata sorted by filing date descending.
        """
        if filing_type not in _VALID_FILING_TYPES:
            raise ValueError(
                f"Unsupported filing type '{filing_type}'. "
                f"Supported: {sorted(_VALID_FILING_TYPES)}"
            )

        cik = self._resolve_cik(ticker)
        data = self._get_json(f"{_SEC_DATA}/submissions/CIK{cik}.json")

        filings: list[FilingMetadata] = []

        # SEC returns recent filings inline, and older ones in separate
        # paginated "files" entries.  We process both.
        recent = data.get("filings", {}).get("recent", {})
        all_filing_sets = [recent]

        # Paginated older filings
        for file_ref in data.get("filings", {}).get("files", []):
            file_name = file_ref.get("name", "")
            if file_name:
                try:
                    extra = self._get_json(f"{_SEC_DATA}/submissions/{file_name}")
                    all_filing_sets.append(extra)
                except Exception:
                    logger.warning("Failed to fetch paginated filings file: %s", file_name)

        for filing_set in all_filing_sets:
            forms = filing_set.get("form", [])
            accessions = filing_set.get("accessionNumber", [])
            dates_raw = filing_set.get("filingDate", [])
            primary_docs = filing_set.get("primaryDocument", [])
            descriptions = filing_set.get("primaryDocDescription", [])

            for i, form in enumerate(forms):
                if form != filing_type:
                    continue

                try:
                    filing_date_val = date.fromisoformat(dates_raw[i])
                except (ValueError, IndexError):
                    continue

                if start and filing_date_val < start:
                    continue
                if end and filing_date_val > end:
                    continue

                accession = accessions[i] if i < len(accessions) else ""
                primary_doc = primary_docs[i] if i < len(primary_docs) else ""
                desc = descriptions[i] if i < len(descriptions) else ""

                # Build the full URL to the primary document.
                # Accession number with dashes removed forms the directory path.
                accession_no_dashes = accession.replace("-", "")
                doc_url = (
                    f"{_SEC_BASE}/Archives/edgar/data/"
                    f"{cik.lstrip('0')}/{accession_no_dashes}/{primary_doc}"
                )

                filings.append(
                    FilingMetadata(
                        accession_number=accession,
                        filing_type=form,
                        filing_date=filing_date_val,
                        primary_document=primary_doc,
                        description=desc,
                        url=doc_url,
                        cik=cik,
                    )
                )

        filings.sort(key=lambda f: f.filing_date, reverse=True)
        logger.info(
            "Fetched %d %s filings for %s (CIK %s)",
            len(filings),
            filing_type,
            ticker.upper(),
            cik,
        )
        return filings

    # ------------------------------------------------------------------
    # Full filing text
    # ------------------------------------------------------------------

    def fetch_filing_text(self, accession_number: str, *, cik: str | None = None, ticker: str | None = None) -> str:
        """Fetch the full text of a filing by accession number.

        You must provide either *cik* or *ticker* so the connector can
        build the correct URL.  If you have a :class:`FilingMetadata` object,
        pass ``cik=meta.cik``.

        Parameters
        ----------
        accession_number:
            The filing's accession number (e.g. ``"0000320193-23-000077"``).
        cik:
            Zero-padded CIK. If not provided, *ticker* must be given.
        ticker:
            Ticker symbol -- used to resolve CIK if *cik* is not supplied.

        Returns
        -------
        str
            Full text (HTML or plain text) of the filing's primary document.
        """
        if cik is None:
            if ticker is None:
                raise ValueError("Either 'cik' or 'ticker' must be provided.")
            cik = self._resolve_cik(ticker)

        cik_numeric = cik.lstrip("0") or "0"
        accession_no_dashes = accession_number.replace("-", "")

        # First get the filing index to find the primary document name.
        index_url = (
            f"{_SEC_BASE}/Archives/edgar/data/"
            f"{cik_numeric}/{accession_no_dashes}/"
        )

        # Try to get the index JSON to find the primary document.
        index_json_url = (
            f"{_SEC_DATA}/submissions/"
            f"{accession_number}.json"
        )
        # Fallback: scrape the index page for the primary document link.
        # The simplest approach is to get the filing index page.
        try:
            index_page = self._get_text(f"{index_url}index.json")
            import json

            idx_data = json.loads(index_page)
            items = idx_data.get("directory", {}).get("item", [])
            # Pick the primary document (usually the first .htm or .txt file
            # that isn't an index or R file).
            primary_doc: str | None = None
            for item in items:
                item_name = item.get("name", "")
                if item_name.endswith((".htm", ".html", ".txt")) and not item_name.startswith(("R", "Financial_Report")):
                    primary_doc = item_name
                    break

            if primary_doc is None and items:
                # Fallback to first document
                primary_doc = items[0].get("name", "")

            if not primary_doc:
                raise FilingNotFoundError(
                    f"Could not determine primary document for accession {accession_number}"
                )

            doc_url = f"{index_url}{primary_doc}"
        except (EdgarError, Exception) as exc:
            logger.debug("Index JSON lookup failed (%s), trying accession directly", exc)
            # Last resort -- build URL from accession assuming common patterns.
            doc_url = f"{index_url}{accession_no_dashes}.txt"

        text = self._get_text(doc_url)
        logger.info(
            "Fetched filing text for accession %s (%d chars)",
            accession_number,
            len(text),
        )
        return text

    # ------------------------------------------------------------------
    # Company facts (structured XBRL data)
    # ------------------------------------------------------------------

    def fetch_company_facts(self, ticker: str) -> dict[str, Any]:
        """Fetch the full XBRL company facts from SEC.

        This is the structured financial data extracted from XBRL-tagged
        filings.  The response contains every reported US-GAAP concept
        with historical values, units, filing dates, and more.

        Parameters
        ----------
        ticker:
            Stock ticker symbol.

        Returns
        -------
        dict
            Raw SEC company facts JSON. The ``"facts"`` key contains
            ``"us-gaap"`` and ``"dei"`` sub-dictionaries.
        """
        cik = self._resolve_cik(ticker)
        data = self._get_json(f"{_SEC_DATA}/api/xbrl/companyfacts/CIK{cik}.json")
        logger.info("Fetched company facts for %s (CIK %s)", ticker.upper(), cik)
        return data

    def _extract_concept_values(
        self,
        facts: dict[str, Any],
        concept: str,
        *,
        period_filter: str = "quarterly",
        unit_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract time-series values for a single XBRL concept.

        Parameters
        ----------
        facts:
            The ``facts["us-gaap"]`` sub-dict from :meth:`fetch_company_facts`.
        concept:
            US-GAAP concept name (e.g. ``"Revenues"``).
        period_filter:
            ``"quarterly"`` keeps only point-in-time or quarter-length
            periods; ``"annual"`` keeps 12-month duration or instant values
            from 10-K filings.
        unit_filter:
            If given, only return values in this unit (e.g. ``"USD"``).

        Returns
        -------
        list[dict]
            Dicts with keys: ``val``, ``end``, ``start`` (optional),
            ``form``, ``filed``, ``accn``, ``fy``, ``fp``.
        """
        concept_data = facts.get(concept)
        if concept_data is None:
            return []

        units = concept_data.get("units", {})
        rows: list[dict[str, Any]] = []

        for unit_key, entries in units.items():
            if unit_filter and unit_key != unit_filter:
                continue
            for entry in entries:
                form = entry.get("form", "")
                fp = entry.get("fp", "")  # FY, Q1, Q2, Q3, Q4
                start_date = entry.get("start")
                end_date = entry.get("end")

                if period_filter == "quarterly":
                    # Keep quarterly entries (Q1-Q4) and filter by duration.
                    if start_date and end_date:
                        try:
                            d_start = date.fromisoformat(start_date)
                            d_end = date.fromisoformat(end_date)
                            duration_days = (d_end - d_start).days
                            # Quarterly filings are roughly 90 days.
                            if duration_days > 200:
                                continue
                        except ValueError:
                            pass
                elif period_filter == "annual":
                    if start_date and end_date:
                        try:
                            d_start = date.fromisoformat(start_date)
                            d_end = date.fromisoformat(end_date)
                            duration_days = (d_end - d_start).days
                            # Annual filings are roughly 365 days.
                            if duration_days < 300:
                                continue
                        except ValueError:
                            pass

                rows.append(
                    {
                        "val": entry.get("val"),
                        "end": end_date or entry.get("end"),
                        "start": start_date,
                        "form": form,
                        "filed": entry.get("filed"),
                        "accn": entry.get("accn"),
                        "fy": entry.get("fy"),
                        "fp": fp,
                        "unit": unit_key,
                    }
                )

        return rows

    # ------------------------------------------------------------------
    # Financial statements (BaseFundamentalConnector interface)
    # ------------------------------------------------------------------

    def fetch_financials(
        self,
        ticker: str,
        statement: str = "income",
        period: str = "quarterly",
    ) -> pl.DataFrame:
        """Fetch a financial statement built from XBRL company facts.

        Implements :class:`BaseFundamentalConnector.fetch_financials`.

        Parameters
        ----------
        ticker:
            Stock ticker symbol.
        statement:
            One of ``"income"``, ``"balance"``, ``"cashflow"``.
        period:
            ``"quarterly"`` or ``"annual"``.

        Returns
        -------
        pl.DataFrame
            DataFrame with one row per period end date and one column per
            financial concept (e.g. ``revenue``, ``net_income``, etc.).
        """
        if statement not in _STATEMENT_CONCEPTS:
            raise ValueError(
                f"Unknown statement type '{statement}'. "
                f"Supported: {sorted(_STATEMENT_CONCEPTS.keys())}"
            )
        if period not in ("quarterly", "annual"):
            raise ValueError(f"Period must be 'quarterly' or 'annual', got '{period}'")

        company_facts = self.fetch_company_facts(ticker)
        us_gaap = company_facts.get("facts", {}).get("us-gaap", {})

        concept_map = _STATEMENT_CONCEPTS[statement]
        columns: dict[str, dict[str, Any]] = {}  # end_date -> {col: val, ...}

        for xbrl_concept, col_name in concept_map.items():
            rows = self._extract_concept_values(
                us_gaap,
                xbrl_concept,
                period_filter=period,
            )
            for row in rows:
                end_date = row.get("end")
                if not end_date:
                    continue

                if end_date not in columns:
                    columns[end_date] = {"period_end": end_date}

                # If this column name is already populated for this date,
                # only overwrite if the existing value is None (handles
                # fallback concept names like multiple revenue concepts).
                if col_name not in columns[end_date] or columns[end_date][col_name] is None:
                    columns[end_date][col_name] = row["val"]

        if not columns:
            logger.warning("No %s data found for %s (%s)", statement, ticker, period)
            return pl.DataFrame()

        records = sorted(columns.values(), key=lambda r: r.get("period_end", ""))

        df = pl.DataFrame(records)

        # Ensure period_end is a proper date column.
        if "period_end" in df.columns:
            df = df.with_columns(pl.col("period_end").str.to_date("%Y-%m-%d"))

        logger.info(
            "Built %s statement for %s (%s): %d periods, %d columns",
            statement,
            ticker.upper(),
            period,
            df.height,
            df.width,
        )
        return df

    # ------------------------------------------------------------------
    # Financial ratios
    # ------------------------------------------------------------------

    def fetch_ratios(self, ticker: str) -> dict[str, Any]:
        """Calculate key financial ratios from the most recent filings.

        Uses the latest available data from company facts.  Ratios that
        cannot be computed (missing data) are returned as ``None``.

        Returned ratios:
        - gross_margin, operating_margin, net_margin
        - current_ratio
        - debt_to_equity
        - return_on_equity (ROE)
        - return_on_assets (ROA)

        Parameters
        ----------
        ticker:
            Stock ticker symbol.

        Returns
        -------
        dict[str, Any]
            Ratio name -> value (float or None).
        """
        company_facts = self.fetch_company_facts(ticker)
        us_gaap = company_facts.get("facts", {}).get("us-gaap", {})

        def _latest(concept: str, period: str = "annual") -> float | None:
            """Get the most recent value for a concept."""
            rows = self._extract_concept_values(us_gaap, concept, period_filter=period)
            if not rows:
                return None
            # Sort by end date descending, take most recent.
            rows.sort(key=lambda r: r.get("end", ""), reverse=True)
            val = rows[0].get("val")
            return float(val) if val is not None else None

        def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
            if numerator is None or denominator is None or denominator == 0:
                return None
            return numerator / denominator

        # Fetch latest values for ratio computation.
        revenue = (
            _latest("Revenues")
            or _latest("RevenueFromContractWithCustomerExcludingAssessedTax")
            or _latest("SalesRevenueNet")
        )
        gross_profit = _latest("GrossProfit")
        operating_income = _latest("OperatingIncomeLoss")
        net_income = _latest("NetIncomeLoss")
        total_assets = _latest("Assets")
        current_assets = _latest("AssetsCurrent")
        current_liabilities = _latest("LiabilitiesCurrent")
        total_liabilities = _latest("Liabilities")
        total_equity = _latest("StockholdersEquity")

        ratios: dict[str, Any] = {
            "ticker": ticker.upper(),
            "gross_margin": _safe_div(gross_profit, revenue),
            "operating_margin": _safe_div(operating_income, revenue),
            "net_margin": _safe_div(net_income, revenue),
            "current_ratio": _safe_div(current_assets, current_liabilities),
            "debt_to_equity": _safe_div(total_liabilities, total_equity),
            "return_on_equity": _safe_div(net_income, total_equity),
            "return_on_assets": _safe_div(net_income, total_assets),
            # Raw values for context.
            "_revenue": revenue,
            "_net_income": net_income,
            "_total_assets": total_assets,
            "_total_equity": total_equity,
        }

        logger.info("Computed ratios for %s: %s", ticker.upper(), {
            k: round(v, 4) if isinstance(v, float) else v
            for k, v in ratios.items()
            if not k.startswith("_")
        })
        return ratios

    # ------------------------------------------------------------------
    # Full-text search
    # ------------------------------------------------------------------

    def search_filings(
        self,
        query: str,
        filing_type: str | None = None,
        start: date | None = None,
        end: date | None = None,
        *,
        max_results: int = 50,
    ) -> pl.DataFrame:
        """Search EDGAR full-text search (EFTS) for filings matching a query.

        Parameters
        ----------
        query:
            Free-text search string.
        filing_type:
            Optional filter by form type (e.g. ``"10-K"``).
        start / end:
            Optional date range for filing dates.
        max_results:
            Maximum number of results to return (capped at 100 by SEC).

        Returns
        -------
        pl.DataFrame
            Columns: ``entity_name``, ``ticker``, ``cik``, ``filing_type``,
            ``filing_date``, ``accession_number``, ``file_url``.
        """
        params: dict[str, Any] = {
            "q": query,
            "dateRange": "custom",
        }

        if filing_type:
            if filing_type not in _VALID_FILING_TYPES:
                raise ValueError(f"Unsupported filing type '{filing_type}'.")
            params["forms"] = filing_type

        if start:
            params["startdt"] = start.isoformat()
        if end:
            params["enddt"] = end.isoformat()

        # EFTS returns up to 100 per page. We clamp to max_results.
        clamped = min(max_results, 100)

        data = self._get_json(f"{_SEC_EFTS}/search-index", params={
            **params,
            "from": 0,
            "size": clamped,
        })

        hits = data.get("hits", {}).get("hits", [])

        records: list[dict[str, Any]] = []
        for hit in hits:
            source = hit.get("_source", {})
            records.append(
                {
                    "entity_name": source.get("entity_name", ""),
                    "ticker": ", ".join(source.get("tickers", [])),
                    "cik": source.get("entity_id", ""),
                    "filing_type": source.get("form_type", ""),
                    "filing_date": source.get("file_date", ""),
                    "accession_number": source.get("file_num", ""),
                    "file_url": source.get("file_url", ""),
                }
            )

        df = pl.DataFrame(records) if records else pl.DataFrame(
            schema={
                "entity_name": pl.Utf8,
                "ticker": pl.Utf8,
                "cik": pl.Utf8,
                "filing_type": pl.Utf8,
                "filing_date": pl.Utf8,
                "accession_number": pl.Utf8,
                "file_url": pl.Utf8,
            }
        )

        logger.info("EDGAR search for '%s' returned %d results", query, df.height)
        return df

    # ------------------------------------------------------------------
    # Convenience: filings as DataFrame
    # ------------------------------------------------------------------

    def fetch_filings_df(
        self,
        ticker: str,
        filing_type: str = "10-K",
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Convenience wrapper: return filings as a Polars DataFrame.

        Same parameters as :meth:`fetch_filings`.
        """
        filings = self.fetch_filings(ticker, filing_type, start, end)
        if not filings:
            return pl.DataFrame(
                schema={
                    "accession_number": pl.Utf8,
                    "filing_type": pl.Utf8,
                    "filing_date": pl.Date,
                    "primary_document": pl.Utf8,
                    "description": pl.Utf8,
                    "url": pl.Utf8,
                    "cik": pl.Utf8,
                }
            )

        records = [
            {
                "accession_number": f.accession_number,
                "filing_type": f.filing_type,
                "filing_date": f.filing_date,
                "primary_document": f.primary_document,
                "description": f.description,
                "url": f.url,
                "cik": f.cik,
            }
            for f in filings
        ]
        return pl.DataFrame(records)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("EdgarConnector: HTTP client closed.")

    def __enter__(self) -> EdgarConnector:
        self.connect()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Register with ConnectorRegistry
# ---------------------------------------------------------------------------

ConnectorRegistry.register("sec_edgar", EdgarConnector)
