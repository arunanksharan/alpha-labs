"""Feature store for computed alpha factors.

Persistent storage backed by Parquet + DuckDB for caching expensive
feature computations across backtest runs.

Layout on disk:
    {base_path}/features/{feature_name}/{TICKER}.parquet
"""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb
import polars as pl

from config.settings import settings

if TYPE_CHECKING:
    from core.features import BaseFeature

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parquet write settings -- consistent with data.storage.store
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


class FeatureStore:
    """Persistent feature store backed by Parquet + DuckDB.

    Stores computed features (alpha factors) for quick retrieval.
    Avoids recomputation of expensive features across backtest runs.

    Parameters
    ----------
    base_path:
        Root directory for feature storage.  Defaults to
        ``settings.data.store_path / "features"``.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        self._base = Path(base_path or settings.data.store_path) / "features"
        self._base.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._db_path = self._base / "_duckdb" / "features.duckdb"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("FeatureStore initialized at %s", self._base)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _feature_dir(self, feature_name: str) -> Path:
        """Return directory for a given feature, creating it if needed."""
        d = self._base / feature_name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _parquet_path(self, feature_name: str, ticker: str) -> Path:
        """Build parquet path: {base}/features/{feature_name}/{TICKER}.parquet."""
        d = self._feature_dir(feature_name)
        return d / f"{_normalize_ticker(ticker)}.parquet"

    def _apply_date_filter(
        self,
        df: pl.DataFrame,
        start: date | None,
        end: date | None,
    ) -> pl.DataFrame:
        """Filter DataFrame on the ``date`` column."""
        if df.is_empty() or "date" not in df.columns:
            return df

        date_col = df["date"]
        if date_col.dtype == pl.Datetime:
            df = df.with_columns(pl.col("date").dt.date().alias("_filter_date"))
        elif date_col.dtype == pl.Date:
            df = df.with_columns(pl.col("date").alias("_filter_date"))
        else:
            df = df.with_columns(pl.col("date").cast(pl.Date).alias("_filter_date"))

        if start is not None:
            df = df.filter(pl.col("_filter_date") >= start)
        if end is not None:
            df = df.filter(pl.col("_filter_date") <= end)

        return df.drop("_filter_date")

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save(self, feature_name: str, ticker: str, data: pl.DataFrame) -> int:
        """Save computed feature values to parquet.

        Merges with existing data, deduplicating on ``date`` (keeps last).
        The *data* DataFrame must contain a ``date`` column.

        Returns the total row count after merge.
        """
        if "date" not in data.columns:
            raise ValueError("Feature data must contain a 'date' column")

        if data.is_empty():
            logger.warning(
                "Skipping write of empty DataFrame for %s/%s", feature_name, ticker
            )
            return 0

        path = self._parquet_path(feature_name, ticker)

        with self._write_lock:
            if path.exists():
                existing = pl.read_parquet(path)
                combined = pl.concat([existing, data], how="diagonal_relaxed")
            else:
                combined = data

            # Dedup on date, keeping the latest write
            combined = combined.unique(subset=["date"], keep="last")
            combined = combined.sort("date")

            combined.write_parquet(path, **_PARQUET_OPTS)
            rows = combined.height
            logger.info(
                "Saved %d rows for feature=%s ticker=%s", rows, feature_name, ticker
            )
            return rows

    def load(
        self,
        feature_name: str,
        ticker: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Load feature values with optional date filtering.

        Returns an empty DataFrame if no data is found.
        """
        path = self._parquet_path(feature_name, ticker)
        if not path.exists():
            logger.debug("No data for feature=%s ticker=%s", feature_name, ticker)
            return pl.DataFrame()

        df = pl.read_parquet(path)
        start_d = _coerce_date(start)
        end_d = _coerce_date(end)
        return self._apply_date_filter(df, start_d, end_d)

    def load_multi(
        self,
        feature_names: list[str],
        ticker: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pl.DataFrame:
        """Load multiple features and join on ``date``.

        Returns a single DataFrame with ``date`` plus all feature columns.
        """
        frames: list[pl.DataFrame] = []
        for name in feature_names:
            df = self.load(name, ticker, start=start, end=end)
            if not df.is_empty():
                frames.append(df)

        if not frames:
            return pl.DataFrame()

        # Join all frames on date
        result = frames[0]
        for df in frames[1:]:
            result = result.join(df, on="date", how="full", suffix=f"_{id(df)}")

        return result.sort("date")

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_features(self) -> list[str]:
        """Return a sorted list of all stored feature names."""
        features: list[str] = []
        if self._base.exists():
            for child in sorted(self._base.iterdir()):
                if (
                    child.is_dir()
                    and not child.name.startswith((".", "_"))
                    and any(child.glob("*.parquet"))
                ):
                    features.append(child.name)
        return features

    def list_tickers(self, feature_name: str) -> list[str]:
        """Return sorted tickers that have data for a given feature."""
        feature_dir = self._base / feature_name
        if not feature_dir.exists():
            return []
        return sorted(
            p.stem
            for p in feature_dir.glob("*.parquet")
            if not p.name.startswith((".", "_"))
        )

    # ------------------------------------------------------------------
    # DuckDB query
    # ------------------------------------------------------------------

    def query(self, sql: str) -> pl.DataFrame:
        """Run arbitrary SQL via DuckDB over the feature parquet files.

        Registers a view for each stored feature, named after the feature.
        Each view exposes a ``filename`` column for provenance.

        Returns a Polars DataFrame.
        """
        conn = duckdb.connect(str(self._db_path), read_only=False)
        try:
            self._register_views(conn)
            result = conn.execute(sql)
            arrow_table = result.arrow()
            return pl.from_arrow(arrow_table)
        except Exception:
            logger.exception("DuckDB query failed: %s", sql)
            raise
        finally:
            conn.close()

    def _register_views(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Create or replace views for each feature directory."""
        for feature_name in self.list_features():
            glob_pattern = str(self._base / feature_name / "*.parquet")
            try:
                conn.execute(
                    f"CREATE OR REPLACE VIEW {feature_name} AS "
                    f"SELECT * FROM read_parquet('{glob_pattern}', "
                    f"union_by_name=true, hive_partitioning=false, filename=true)"
                )
            except duckdb.IOException:
                pass

    # ------------------------------------------------------------------
    # Compute convenience
    # ------------------------------------------------------------------

    def compute_and_store(
        self,
        feature: BaseFeature,
        data: pl.DataFrame,
        ticker: str,
    ) -> pl.DataFrame:
        """Compute a feature, persist the result, and return the enhanced DataFrame.

        Validates that *data* has sufficient lookback before computing.

        Raises
        ------
        ValueError
            If the input data does not have enough rows for the feature's
            lookback window.
        """
        if not feature.validate(data):
            raise ValueError(
                f"Insufficient data for feature '{feature.name}': "
                f"need {feature.lookback_days} rows, got {len(data)}"
            )

        result = feature.compute(data)

        # Identify new columns added by the feature (beyond original)
        original_cols = set(data.columns)
        feature_cols = [c for c in result.columns if c not in original_cols]

        if not feature_cols:
            logger.warning(
                "Feature '%s' did not add any new columns", feature.name
            )
            return result

        # Save only date + feature columns
        cols_to_save = ["date"] + feature_cols
        available = [c for c in cols_to_save if c in result.columns]
        feature_df = result.select(available)

        self.save(feature.name, ticker, feature_df)
        logger.info(
            "Computed and stored feature=%s ticker=%s cols=%s",
            feature.name,
            ticker,
            feature_cols,
        )
        return result

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return storage statistics: total features, files, and disk usage."""
        total_files = 0
        total_bytes = 0

        for pq in self._base.rglob("*.parquet"):
            total_files += 1
            total_bytes += pq.stat().st_size

        features = self.list_features()

        return {
            "base_path": str(self._base),
            "total_features": len(features),
            "total_files": total_files,
            "disk_bytes": total_bytes,
            "disk_mb": round(total_bytes / (1024 * 1024), 2),
            "features": features,
        }

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        features = self.list_features()
        return f"FeatureStore(base={self._base!s}, features={len(features)})"
