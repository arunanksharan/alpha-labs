"""Shared utilities for consistent data handling across the platform."""

from __future__ import annotations

import polars as pl


def normalize_date_column(df: pl.DataFrame, col: str = "date") -> pl.DataFrame:
    """Normalize a date column to pl.Date regardless of input type.

    Handles: pl.Date (passthrough), pl.Datetime (extract date), pl.Utf8 (parse).
    This ensures consistent date types across all modules.
    """
    if col not in df.columns:
        return df
    dtype = df[col].dtype
    if dtype == pl.Date:
        return df
    if isinstance(dtype, pl.Datetime):
        return df.with_columns(pl.col(col).dt.date().alias(col))
    if dtype == pl.Utf8:
        return df.with_columns(pl.col(col).str.to_date().alias(col))
    return df
