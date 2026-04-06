"""Production storage layer for the quant research platform.

Architecture:
    - Parquet files: primary storage for columnar data (write-once, read-fast)
    - DuckDB: analytical query engine over parquet (not primary storage)

Layout on disk:
    {base_path}/
        ohlcv/{TICKER}/{interval}.parquet
        fundamentals/{TICKER}/{statement_type}.parquet
        macro/{series_id}/data.parquet
        filings/{TICKER}/filings.parquet
        _duckdb/analytics.duckdb          (ephemeral, rebuilt from parquet)
"""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parquet write settings -- tuned for analytical read patterns
# ---------------------------------------------------------------------------
_PARQUET_OPTS: dict[str, Any] = {
    "compression": "zstd",
    "compression_level": 3,
    "statistics": True,
    "row_group_size": 100_000,
    "use_pyarrow": True,
}


def _normalize_ticker(ticker: str) -> str:
    """Normalize ticker to uppercase, filesystem-safe form."""
    return ticker.upper().replace("/", "_").replace("\\", "_").strip()


def _coerce_date(val: str | date | datetime | None) -> date | None:
    """Coerce various date representations to ``datetime.date``."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date string: {val!r}")
    raise TypeError(f"Unsupported date type: {type(val)}")


class DataStore:
    """Unified storage layer backed by Parquet files with DuckDB query support.

    Thread-safe for concurrent reads.  Writes are serialized via a lock to
    guarantee append-merge correctness.

    Parameters
    ----------
    base_path:
        Root directory for all stored data.  Created automatically.
    """

    def __init__(self, base_path: Path = Path("data/store")) -> None:
        self._base = Path(base_path).resolve()
        self._write_lock = threading.Lock()

        # Create directory skeleton
        for subdir in ("ohlcv", "fundamentals", "macro", "filings", "_duckdb"):
            (self._base / subdir).mkdir(parents=True, exist_ok=True)

        self._db_path = self._base / "_duckdb" / "analytics.duckdb"
        logger.info("DataStore initialized at %s", self._base)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parquet_path(self, *parts: str) -> Path:
        """Build a parquet file path from path segments under base."""
        p = self._base.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _merge_and_write(
        self,
        path: Path,
        incoming: pl.DataFrame,
        dedup_cols: list[str],
        sort_cols: list[str],
    ) -> int:
        """Merge *incoming* data with any existing parquet file.

        De-duplicates on *dedup_cols* keeping the **last** occurrence (i.e.
        the freshest write wins).  Returns the total row count written.
        """
        if incoming.is_empty():
            logger.warning("Skipping write of empty DataFrame to %s", path)
            return 0

        with self._write_lock:
            if path.exists():
                existing = pl.read_parquet(path)
                combined = pl.concat([existing, incoming], how="diagonal_relaxed")
            else:
                combined = incoming

            # Keep last occurrence per dedup key
            available_dedup = [c for c in dedup_cols if c in combined.columns]
            if available_dedup:
                combined = combined.unique(subset=available_dedup, keep="last")

            available_sort = [c for c in sort_cols if c in combined.columns]
            if available_sort:
                combined = combined.sort(available_sort)

            combined.write_parquet(path, **_PARQUET_OPTS)
            rows = combined.height
            logger.info(
                "Wrote %d rows to %s (merged with existing: %s)",
                rows,
                path,
                path.exists(),
            )
            return rows

    def _duckdb_conn(self) -> duckdb.DuckDBPyConnection:
        """Return a *new* read-only DuckDB connection wired to our parquet tree.

        Each call creates a fresh connection so callers on different threads
        never share mutable state.
        """
        conn = duckdb.connect(str(self._db_path), read_only=False)
        # Register parquet glob views so SQL can reference them by name
        self._register_views(conn)
        return conn

    def _register_views(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Create or replace views that point at the parquet files on disk."""
        globs: dict[str, str] = {
            "ohlcv": str(self._base / "ohlcv" / "*" / "*.parquet"),
            "fundamentals": str(self._base / "fundamentals" / "*" / "*.parquet"),
            "macro": str(self._base / "macro" / "*" / "*.parquet"),
            "filings": str(self._base / "filings" / "*" / "*.parquet"),
        }
        for view_name, glob_pattern in globs.items():
            try:
                conn.execute(
                    f"CREATE OR REPLACE VIEW {view_name} AS "
                    f"SELECT * FROM read_parquet('{glob_pattern}', union_by_name=true, "
                    f"hive_partitioning=false, filename=true)"
                )
            except duckdb.IOException:
                # No files yet for this category -- skip silently
                pass

    # ------------------------------------------------------------------
    # OHLCV
    # ------------------------------------------------------------------

    def save_ohlcv(
        self,
        ticker: str,
        data: pl.DataFrame,
        source: str,
        interval: str = "1d",
    ) -> int:
        """Persist OHLCV data for *ticker* at the given *interval*.

        A ``source`` metadata column is attached so provenance is tracked.
        Returns the total number of rows stored after merge.
        """
        ticker = _normalize_ticker(ticker)
        df = data.clone()

        # Attach metadata columns if missing
        if "ticker" not in df.columns:
            df = df.with_columns(pl.lit(ticker).alias("ticker"))
        if "source" not in df.columns:
            df = df.with_columns(pl.lit(source).alias("source"))
        if "interval" not in df.columns:
            df = df.with_columns(pl.lit(interval).alias("interval"))

        path = self._parquet_path("ohlcv", ticker, f"{interval}.parquet")
        rows = self._merge_and_write(path, df, dedup_cols=["date"], sort_cols=["date"])
        logger.info(
            "save_ohlcv: ticker=%s interval=%s source=%s rows=%d", ticker, interval, source, rows
        )
        return rows

    def load_ohlcv(
        self,
        ticker: str,
        start: str | date | None = None,
        end: str | date | None = None,
        interval: str = "1d",
    ) -> pl.DataFrame:
        """Load OHLCV data for *ticker* with optional date filtering."""
        ticker = _normalize_ticker(ticker)
        path = self._parquet_path("ohlcv", ticker, f"{interval}.parquet")
        if not path.exists():
            logger.warning("No OHLCV data for %s/%s", ticker, interval)
            return pl.DataFrame()

        df = pl.read_parquet(path)

        start_d = _coerce_date(start)
        end_d = _coerce_date(end)
        if "date" in df.columns:
            date_col = df["date"]
            # Cast to date if stored as datetime
            if date_col.dtype in (pl.Datetime, pl.Date):
                if date_col.dtype == pl.Datetime:
                    df = df.with_columns(pl.col("date").dt.date().alias("_filter_date"))
                else:
                    df = df.with_columns(pl.col("date").alias("_filter_date"))
            else:
                # String dates -- cast via strptime
                df = df.with_columns(
                    pl.col("date").cast(pl.Date).alias("_filter_date")
                )
            if start_d is not None:
                df = df.filter(pl.col("_filter_date") >= start_d)
            if end_d is not None:
                df = df.filter(pl.col("_filter_date") <= end_d)
            df = df.drop("_filter_date")

        return df

    # ------------------------------------------------------------------
    # Fundamentals
    # ------------------------------------------------------------------

    def save_fundamentals(
        self,
        ticker: str,
        data: pl.DataFrame,
        statement_type: str,
    ) -> int:
        """Persist fundamental data (income / balance / cashflow).

        Returns total rows after merge.
        """
        ticker = _normalize_ticker(ticker)
        statement_type = statement_type.lower().strip()
        df = data.clone()

        if "ticker" not in df.columns:
            df = df.with_columns(pl.lit(ticker).alias("ticker"))
        if "statement_type" not in df.columns:
            df = df.with_columns(pl.lit(statement_type).alias("statement_type"))

        path = self._parquet_path("fundamentals", ticker, f"{statement_type}.parquet")
        # Dedup on date + statement_type to handle quarterly re-statements
        rows = self._merge_and_write(
            path, df, dedup_cols=["date", "statement_type"], sort_cols=["date"]
        )
        logger.info(
            "save_fundamentals: ticker=%s type=%s rows=%d", ticker, statement_type, rows
        )
        return rows

    def load_fundamentals(
        self,
        ticker: str,
        statement_type: str | None = None,
    ) -> pl.DataFrame:
        """Load fundamental data.  If *statement_type* is None, load all."""
        ticker = _normalize_ticker(ticker)
        fund_dir = self._base / "fundamentals" / ticker

        if not fund_dir.exists():
            logger.warning("No fundamental data for %s", ticker)
            return pl.DataFrame()

        if statement_type is not None:
            path = fund_dir / f"{statement_type.lower().strip()}.parquet"
            if not path.exists():
                return pl.DataFrame()
            return pl.read_parquet(path)

        # Load all statement types
        frames: list[pl.DataFrame] = []
        for pq in sorted(fund_dir.glob("*.parquet")):
            frames.append(pl.read_parquet(pq))
        if not frames:
            return pl.DataFrame()
        return pl.concat(frames, how="diagonal_relaxed")

    # ------------------------------------------------------------------
    # Macro
    # ------------------------------------------------------------------

    def save_macro(self, series_id: str, data: pl.DataFrame) -> int:
        """Persist macroeconomic time-series data (GDP, CPI, Fed Funds, etc.)."""
        series_id = series_id.upper().strip()
        df = data.clone()

        if "series_id" not in df.columns:
            df = df.with_columns(pl.lit(series_id).alias("series_id"))

        path = self._parquet_path("macro", series_id, "data.parquet")
        rows = self._merge_and_write(path, df, dedup_cols=["date"], sort_cols=["date"])
        logger.info("save_macro: series=%s rows=%d", series_id, rows)
        return rows

    def load_macro(
        self,
        series_id: str,
        start: str | date | None = None,
        end: str | date | None = None,
    ) -> pl.DataFrame:
        """Load macro series with optional date filtering."""
        series_id = series_id.upper().strip()
        path = self._base / "macro" / series_id / "data.parquet"
        if not path.exists():
            logger.warning("No macro data for series %s", series_id)
            return pl.DataFrame()

        df = pl.read_parquet(path)
        start_d = _coerce_date(start)
        end_d = _coerce_date(end)

        if "date" in df.columns:
            date_col = df["date"]
            if date_col.dtype == pl.Datetime:
                df = df.with_columns(pl.col("date").dt.date().alias("_filter_date"))
            elif date_col.dtype == pl.Date:
                df = df.with_columns(pl.col("date").alias("_filter_date"))
            else:
                df = df.with_columns(pl.col("date").cast(pl.Date).alias("_filter_date"))

            if start_d is not None:
                df = df.filter(pl.col("_filter_date") >= start_d)
            if end_d is not None:
                df = df.filter(pl.col("_filter_date") <= end_d)
            df = df.drop("_filter_date")

        return df

    # ------------------------------------------------------------------
    # Filings
    # ------------------------------------------------------------------

    def save_filings(self, ticker: str, filings: pl.DataFrame) -> int:
        """Persist SEC filings metadata for *ticker*."""
        ticker = _normalize_ticker(ticker)
        df = filings.clone()

        if "ticker" not in df.columns:
            df = df.with_columns(pl.lit(ticker).alias("ticker"))

        path = self._parquet_path("filings", ticker, "filings.parquet")
        # Dedup on accession number if available, else date + filing_type
        dedup = (
            ["accession_number"]
            if "accession_number" in df.columns
            else ["date", "filing_type"]
        )
        rows = self._merge_and_write(path, df, dedup_cols=dedup, sort_cols=["date"])
        logger.info("save_filings: ticker=%s rows=%d", ticker, rows)
        return rows

    def load_filings(
        self,
        ticker: str,
        filing_type: str | None = None,
    ) -> pl.DataFrame:
        """Load filings metadata, optionally filtered by type (10-K, 10-Q, etc.)."""
        ticker = _normalize_ticker(ticker)
        path = self._base / "filings" / ticker / "filings.parquet"
        if not path.exists():
            logger.warning("No filings data for %s", ticker)
            return pl.DataFrame()

        df = pl.read_parquet(path)
        if filing_type is not None and "filing_type" in df.columns:
            df = df.filter(pl.col("filing_type") == filing_type)
        return df

    # ------------------------------------------------------------------
    # DuckDB analytical queries
    # ------------------------------------------------------------------

    def query(self, sql: str) -> pl.DataFrame:
        """Run arbitrary SQL over all stored data via DuckDB.

        Views available: ``ohlcv``, ``fundamentals``, ``macro``, ``filings``.
        Each view exposes a ``filename`` column showing the source parquet path.

        Returns a Polars DataFrame.
        """
        conn = self._duckdb_conn()
        try:
            result = conn.execute(sql)
            # Fetch as Arrow for zero-copy into Polars
            arrow_table = result.arrow()
            return pl.from_arrow(arrow_table)
        except Exception:
            logger.exception("DuckDB query failed: %s", sql)
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    def list_tickers(self) -> list[str]:
        """Return a sorted, deduplicated list of all tickers with any stored data."""
        tickers: set[str] = set()
        for data_dir in ("ohlcv", "fundamentals", "filings"):
            parent = self._base / data_dir
            if parent.exists():
                for child in parent.iterdir():
                    if child.is_dir() and not child.name.startswith((".", "_")):
                        tickers.add(child.name)
        return sorted(tickers)

    def list_date_range(self, ticker: str) -> tuple[date | None, date | None]:
        """Return (min_date, max_date) across all OHLCV intervals for *ticker*."""
        ticker = _normalize_ticker(ticker)
        ohlcv_dir = self._base / "ohlcv" / ticker
        if not ohlcv_dir.exists():
            return (None, None)

        min_d: date | None = None
        max_d: date | None = None

        for pq in ohlcv_dir.glob("*.parquet"):
            df = pl.read_parquet(pq, columns=["date"])
            if df.is_empty() or "date" not in df.columns:
                continue

            col = df["date"]
            if col.dtype == pl.Datetime:
                col = col.dt.date()
            elif col.dtype != pl.Date:
                col = col.cast(pl.Date)

            local_min = col.min()
            local_max = col.max()
            if local_min is not None:
                min_d = local_min if min_d is None else min(min_d, local_min)
            if local_max is not None:
                max_d = local_max if max_d is None else max(max_d, local_max)

        return (min_d, max_d)

    def get_stats(self) -> dict[str, Any]:
        """Return storage statistics: total files, rows, and disk usage."""
        total_files = 0
        total_rows = 0
        total_bytes = 0

        for pq in self._base.rglob("*.parquet"):
            total_files += 1
            total_bytes += pq.stat().st_size
        for pq in self._base.rglob("*.parquet"):
            try:
                lf = pl.scan_parquet(pq)
                total_rows += lf.select(pl.len()).collect().item()
            except Exception:
                pass

        # DuckDB file size
        duckdb_bytes = 0
        if self._db_path.exists():
            duckdb_bytes = self._db_path.stat().st_size

        return {
            "base_path": str(self._base),
            "parquet_files": total_files,
            "total_rows": total_rows,
            "parquet_disk_bytes": total_bytes,
            "parquet_disk_mb": round(total_bytes / (1024 * 1024), 2),
            "duckdb_disk_bytes": duckdb_bytes,
            "duckdb_disk_mb": round(duckdb_bytes / (1024 * 1024), 2),
            "tickers": len(self.list_tickers()),
            "categories": {
                "ohlcv": len(list((self._base / "ohlcv").rglob("*.parquet")))
                if (self._base / "ohlcv").exists()
                else 0,
                "fundamentals": len(
                    list((self._base / "fundamentals").rglob("*.parquet"))
                )
                if (self._base / "fundamentals").exists()
                else 0,
                "macro": len(list((self._base / "macro").rglob("*.parquet")))
                if (self._base / "macro").exists()
                else 0,
                "filings": len(list((self._base / "filings").rglob("*.parquet")))
                if (self._base / "filings").exists()
                else 0,
            },
        }

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def vacuum(self) -> None:
        """Rewrite all parquet files to reclaim space after many merges.

        Re-sorts and re-compresses every file.  Safe to call periodically.
        """
        count = 0
        for pq in self._base.rglob("*.parquet"):
            try:
                df = pl.read_parquet(pq)
                if "date" in df.columns:
                    df = df.sort("date")
                df.write_parquet(pq, **_PARQUET_OPTS)
                count += 1
            except Exception:
                logger.exception("vacuum: failed to rewrite %s", pq)
        logger.info("vacuum: rewrote %d parquet files", count)

    def destroy(self) -> None:
        """Delete ALL stored data.  Irreversible.  Use with care."""
        import shutil

        logger.warning("DESTROYING all data at %s", self._base)
        shutil.rmtree(self._base)
        # Recreate skeleton
        self.__init__(base_path=self._base)  # type: ignore[misc]

    def __repr__(self) -> str:
        tickers = len(self.list_tickers())
        return f"DataStore(base={self._base!s}, tickers={tickers})"
