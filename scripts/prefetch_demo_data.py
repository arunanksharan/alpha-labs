#!/usr/bin/env python3
"""Pre-fetch demo data for Singapore meetup.

Run once before the demo to populate the DataStore.
Works offline after this — no internet needed during presentation.

Usage:
    PYTHONPATH=. python scripts/prefetch_demo_data.py
"""

import logging
import sys
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

DEMO_TICKERS = ["AAPL", "MSFT", "NVDA", "GOOG", "TSLA", "META", "AMZN", "JPM", "SPY", "QQQ"]
START_DATE = date(2020, 1, 1)
END_DATE = date(2024, 12, 31)


def main() -> None:
    from data.fetchers.yfinance_connector import YFinanceConnector
    from data.storage.store import DataStore

    store = DataStore()
    connector = YFinanceConnector()

    logger.info("Pre-fetching %d tickers: %s", len(DEMO_TICKERS), ", ".join(DEMO_TICKERS))
    logger.info("Date range: %s to %s", START_DATE, END_DATE)

    success = 0
    for ticker in DEMO_TICKERS:
        try:
            logger.info("Fetching %s...", ticker)
            data = connector.fetch_ohlcv(ticker, START_DATE, END_DATE)
            rows = store.save_ohlcv(ticker, data, source="yfinance")
            logger.info("  %s: %d rows saved", ticker, rows)
            success += 1
        except Exception as e:
            logger.error("  %s: FAILED — %s", ticker, e)

    logger.info("")
    logger.info("Done: %d/%d tickers fetched successfully", success, len(DEMO_TICKERS))
    logger.info("Data stored at: %s", store._base)

    # Show stats
    stats = store.get_stats()
    logger.info("Store stats: %d files, %d total rows, %.1f MB",
                stats["parquet_files"], stats["total_rows"], stats["parquet_disk_mb"])

    if success < len(DEMO_TICKERS):
        sys.exit(1)


if __name__ == "__main__":
    main()
