#!/usr/bin/env python3
"""Pre-fetch market data and compute signals for the research universe.

Populates the DataStore with OHLCV data from YFinance, then runs the
full research pipeline (features → signals → backtest) for each ticker.
Results are cached — the dashboard loads instantly from Parquet.

Usage:
    PYTHONPATH=. python scripts/prefetch_demo_data.py
    PYTHONPATH=. python scripts/prefetch_demo_data.py --tickers D05.SI,RELIANCE.NS
    PYTHONPATH=. python scripts/prefetch_demo_data.py --add TCS.NS
"""

import argparse
import json
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

UNIVERSE_FILE = Path("data/universe.json")

DEFAULT_UNIVERSE = {
    "tickers": [
        # Singapore — SGX
        "D05.SI",   # DBS Group
        "O39.SI",   # OCBC Bank
        "U11.SI",   # UOB
        "C6L.SI",   # Singapore Airlines
        # India — NSE
        "RELIANCE.NS",  # Reliance Industries
        "TCS.NS",       # TCS
        "INFY.NS",      # Infosys
        "HDFCBANK.NS",  # HDFC Bank
        # US — Reference
        "AAPL",
        "NVDA",
    ],
    "start_date": "2022-01-01",
    "strategies": ["mean_reversion", "momentum"],
}


def load_universe() -> dict:
    """Load universe config, creating default if missing."""
    if UNIVERSE_FILE.exists():
        return json.loads(UNIVERSE_FILE.read_text())
    UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    UNIVERSE_FILE.write_text(json.dumps(DEFAULT_UNIVERSE, indent=2))
    logger.info("Created default universe at %s", UNIVERSE_FILE)
    return DEFAULT_UNIVERSE


def save_universe(universe: dict) -> None:
    UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    UNIVERSE_FILE.write_text(json.dumps(universe, indent=2))


def fetch_data(tickers: list[str], start_date: str) -> dict[str, int]:
    """Fetch OHLCV data for all tickers and save to Parquet store."""
    from data.fetchers.yfinance_connector import YFinanceConnector
    from data.storage.store import DataStore

    store = DataStore()
    connector = YFinanceConnector()
    end = date.today()
    start = date.fromisoformat(start_date) if isinstance(start_date, str) else start_date
    results = {}

    for ticker in tickers:
        try:
            logger.info("Fetching %s (%s → %s)...", ticker, start, end)
            data = connector.fetch_ohlcv(ticker, start, end)
            rows = store.save_ohlcv(ticker, data, source="yfinance")
            results[ticker] = rows
            logger.info("  %s: %d rows cached", ticker, rows)
            time.sleep(0.5)  # Rate limit
        except Exception as e:
            logger.error("  %s: FAILED — %s", ticker, e)
            results[ticker] = 0

    return results


def compute_signals(tickers: list[str], strategies: list[str], start_date: str) -> dict:
    """Run research pipeline for each ticker × strategy and cache results."""
    from core.orchestrator import ResearchOrchestrator

    orchestrator = ResearchOrchestrator()
    end = date.today().isoformat()
    results_cache = {}
    cache_dir = Path("data/cache/research")
    cache_dir.mkdir(parents=True, exist_ok=True)

    for ticker in tickers:
        for strategy in strategies:
            key = f"{ticker}__{strategy}"
            try:
                logger.info("Running %s / %s...", ticker, strategy)
                result = orchestrator.run(ticker, strategy, start_date, end)
                result_json = result.to_json()

                # Cache to disk
                cache_file = cache_dir / f"{key}.json"
                cache_file.write_text(json.dumps(result_json, default=str))

                bt = result_json.get("backtest", {})
                logger.info(
                    "  %s/%s: %d signals, Sharpe %.2f, Return %.2f%%",
                    ticker, strategy,
                    result_json.get("signals_count", 0),
                    bt.get("sharpe_ratio", 0),
                    bt.get("total_return", 0) * 100,
                )
                results_cache[key] = {
                    "signals": result_json.get("signals_count", 0),
                    "sharpe": bt.get("sharpe_ratio", 0),
                    "total_return": bt.get("total_return", 0),
                }
            except Exception as e:
                logger.error("  %s/%s: FAILED — %s", ticker, strategy, e)
                results_cache[key] = {"error": str(e)}

    return results_cache


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-fetch data and compute signals")
    parser.add_argument("--tickers", type=str, help="Comma-separated tickers (overrides universe)")
    parser.add_argument("--add", type=str, help="Add ticker(s) to universe (comma-separated)")
    parser.add_argument("--remove", type=str, help="Remove ticker(s) from universe")
    parser.add_argument("--list", action="store_true", help="List current universe")
    parser.add_argument("--data-only", action="store_true", help="Only fetch data, skip signal computation")
    parser.add_argument("--signals-only", action="store_true", help="Only compute signals from cached data")
    args = parser.parse_args()

    universe = load_universe()

    # List
    if args.list:
        print(f"Universe ({len(universe['tickers'])} tickers):")
        for t in universe["tickers"]:
            print(f"  {t}")
        print(f"Start date: {universe['start_date']}")
        print(f"Strategies: {', '.join(universe['strategies'])}")
        return

    # Add/Remove
    if args.add:
        new_tickers = [t.strip().upper() for t in args.add.split(",")]
        for t in new_tickers:
            if t not in universe["tickers"]:
                universe["tickers"].append(t)
                logger.info("Added %s to universe", t)
        save_universe(universe)

    if args.remove:
        rm_tickers = [t.strip().upper() for t in args.remove.split(",")]
        universe["tickers"] = [t for t in universe["tickers"] if t not in rm_tickers]
        save_universe(universe)
        logger.info("Removed %s from universe", args.remove)
        return

    # Determine tickers
    tickers = universe["tickers"]
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",")]

    start_date = universe.get("start_date", "2022-01-01")
    strategies = universe.get("strategies", ["mean_reversion"])

    logger.info("=" * 60)
    logger.info("AGENTIC ALPHA LAB — Data Refresh")
    logger.info("=" * 60)
    logger.info("Universe: %d tickers", len(tickers))
    logger.info("Tickers: %s", ", ".join(tickers))
    logger.info("Date range: %s → today", start_date)
    logger.info("Strategies: %s", ", ".join(strategies))
    logger.info("")

    # Step 1: Fetch data
    if not args.signals_only:
        logger.info("STEP 1: Fetching market data...")
        fetch_results = fetch_data(tickers, start_date)
        fetched = sum(1 for v in fetch_results.values() if v > 0)
        logger.info("Data: %d/%d tickers fetched", fetched, len(tickers))
        logger.info("")

    # Step 2: Compute signals
    if not args.data_only:
        logger.info("STEP 2: Computing signals & backtests...")
        signal_results = compute_signals(tickers, strategies, start_date)
        logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("COMPLETE")
    logger.info("=" * 60)

    from data.storage.store import DataStore
    store = DataStore()
    stats = store.get_stats()
    logger.info("Store: %d files, %d rows, %.1f MB",
                stats["parquet_files"], stats["total_rows"], stats["parquet_disk_mb"])

    cache_dir = Path("data/cache/research")
    cached = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    logger.info("Cached research results: %d", len(cached))


if __name__ == "__main__":
    main()
