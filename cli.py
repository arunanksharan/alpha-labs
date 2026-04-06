"""CLI interface for the quant research platform.

Usage:
    python -m cli fetch --source yfinance --ticker AAPL --start 2020-01-01
    python -m cli fetch --source yfinance --tickers AAPL,MSFT,GOOG --start 2020-01-01
    python -m cli fetch --source fred --series DFF,DGS10,T10Y2Y --start 2020-01-01
    python -m cli fetch --source edgar --ticker AAPL --filing-type 10-K
    python -m cli analyze --ticker AAPL --metrics sharpe,sortino,max_drawdown
    python -m cli stats --ticker AAPL --tests adf,hurst,jarque_bera
    python -m cli store --list
    python -m cli store --info AAPL
"""

import argparse
import logging
import sys
from datetime import date, datetime

import polars as pl

from config.settings import settings


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_fetch(args: argparse.Namespace) -> None:
    """Fetch data from a connector and store it."""
    from core.connectors import ConnectorRegistry
    from data.storage.store import DataStore

    store = DataStore()

    if args.source == "yfinance":
        connector = ConnectorRegistry.get("yfinance")
        tickers = args.tickers.split(",") if args.tickers else [args.ticker]
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = (
            datetime.strptime(args.end, "%Y-%m-%d").date()
            if args.end
            else date.today()
        )
        interval = args.interval or "1d"

        if len(tickers) == 1:
            data = connector.fetch_ohlcv(tickers[0], start, end, interval)
            store.save_ohlcv(tickers[0], data, source="yfinance")
            print(f"Fetched {len(data)} rows for {tickers[0]}")
            print(data.head(5))
        else:
            results = connector.fetch_multiple(tickers, start, end, interval)
            for ticker, data in results.items():
                store.save_ohlcv(ticker, data, source="yfinance")
                print(f"Fetched {len(data)} rows for {ticker}")

    elif args.source == "fred":
        connector = ConnectorRegistry.get("fred")
        series_ids = args.series.split(",")
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = (
            datetime.strptime(args.end, "%Y-%m-%d").date()
            if args.end
            else date.today()
        )

        if len(series_ids) == 1:
            data = connector.fetch_series(series_ids[0], start, end)
            store.save_macro(series_ids[0], data)
            print(f"Fetched {len(data)} rows for {series_ids[0]}")
            print(data.head(5))
        else:
            data = connector.fetch_multiple_series(series_ids, start, end)
            for sid in series_ids:
                store.save_macro(sid, data.select(["date", sid]))
            print(f"Fetched {len(data)} rows for {len(series_ids)} series")
            print(data.head(5))

    elif args.source == "edgar":
        connector = ConnectorRegistry.get("sec_edgar")
        filing_type = args.filing_type or "10-K"
        filings = connector.fetch_filings(
            args.ticker,
            filing_type,
            datetime.strptime(args.start, "%Y-%m-%d").date() if args.start else None,
            datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else None,
        )
        store.save_filings(args.ticker, filings)
        print(f"Fetched {len(filings)} {filing_type} filings for {args.ticker}")

    else:
        available = ConnectorRegistry.list_connectors()
        print(f"Unknown source: {args.source}. Available: {', '.join(available)}")
        sys.exit(1)


def cmd_analyze(args: argparse.Namespace) -> None:
    """Run return/risk analytics on stored data."""
    from analytics.returns import (
        compute_returns,
        compute_sharpe,
        compute_sortino,
        compute_max_drawdown,
        compute_calmar,
        compute_var,
        compute_cvar,
        compute_volatility,
        compute_drawdown,
    )
    from data.storage.store import DataStore

    store = DataStore()
    start = datetime.strptime(args.start, "%Y-%m-%d").date() if args.start else None
    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else None
    prices = store.load_ohlcv(args.ticker, start, end)

    if prices.is_empty():
        print(f"No data found for {args.ticker}. Run 'fetch' first.")
        sys.exit(1)

    returns = compute_returns(prices)
    return_col = "log_return" if "log_return" in returns.columns else returns.columns[-1]
    return_series = returns[return_col].drop_nulls()

    metrics = args.metrics.split(",") if args.metrics else [
        "sharpe", "sortino", "max_drawdown", "calmar", "var", "cvar"
    ]

    print(f"\n{'='*50}")
    print(f"  Analytics for {args.ticker}")
    print(f"  Period: {prices['date'].min()} to {prices['date'].max()}")
    print(f"  Observations: {len(return_series)}")
    print(f"{'='*50}\n")

    metric_funcs = {
        "sharpe": lambda: compute_sharpe(returns),
        "sortino": lambda: compute_sortino(returns),
        "max_drawdown": lambda: compute_max_drawdown(returns),
        "calmar": lambda: compute_calmar(returns),
        "var": lambda: compute_var(returns),
        "cvar": lambda: compute_cvar(returns),
    }

    for metric in metrics:
        if metric in metric_funcs:
            value = metric_funcs[metric]()
            print(f"  {metric:.<30} {value:>10.4f}")
        else:
            print(f"  {metric:.<30} {'unknown':>10}")

    print()


def cmd_stats(args: argparse.Namespace) -> None:
    """Run statistical tests on stored data."""
    from analytics.statistics import (
        adf_test,
        hurst_exponent,
        jarque_bera_test,
        ljung_box_test,
        half_life_mean_reversion,
    )
    from analytics.returns import compute_returns
    from data.storage.store import DataStore

    store = DataStore()
    start = datetime.strptime(args.start, "%Y-%m-%d").date() if args.start else None
    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else None
    prices = store.load_ohlcv(args.ticker, start, end)

    if prices.is_empty():
        print(f"No data found for {args.ticker}. Run 'fetch' first.")
        sys.exit(1)

    returns = compute_returns(prices)
    close_prices = prices["close"]
    return_col = "log_return" if "log_return" in returns.columns else returns.columns[-1]
    return_series = returns[return_col].drop_nulls()

    tests = args.tests.split(",") if args.tests else [
        "adf", "hurst", "jarque_bera", "ljung_box", "half_life"
    ]

    print(f"\n{'='*50}")
    print(f"  Statistical Tests for {args.ticker}")
    print(f"  Period: {prices['date'].min()} to {prices['date'].max()}")
    print(f"{'='*50}\n")

    if "adf" in tests:
        result = adf_test(close_prices)
        status = "STATIONARY" if result["is_stationary"] else "NON-STATIONARY"
        print(f"  ADF Test (prices):     stat={result['test_stat']:.4f}  p={result['p_value']:.4f}  [{status}]")

        result_ret = adf_test(return_series)
        status_ret = "STATIONARY" if result_ret["is_stationary"] else "NON-STATIONARY"
        print(f"  ADF Test (returns):    stat={result_ret['test_stat']:.4f}  p={result_ret['p_value']:.4f}  [{status_ret}]")

    if "hurst" in tests:
        h = hurst_exponent(close_prices)
        regime = "MEAN-REVERTING" if h < 0.5 else "TRENDING" if h > 0.5 else "RANDOM WALK"
        print(f"  Hurst Exponent:        H={h:.4f}  [{regime}]")

    if "jarque_bera" in tests:
        result = jarque_bera_test(return_series)
        status = "NORMAL" if result["is_normal"] else "NON-NORMAL"
        print(f"  Jarque-Bera:           stat={result['stat']:.4f}  p={result['p_value']:.6f}  skew={result['skewness']:.4f}  kurt={result['kurtosis']:.4f}  [{status}]")

    if "ljung_box" in tests:
        result = ljung_box_test(return_series)
        status = "AUTOCORRELATED" if result["is_autocorrelated"] else "NO AUTOCORRELATION"
        print(f"  Ljung-Box (lag=10):    stat={result['stat']:.4f}  p={result['p_value']:.4f}  [{status}]")

    if "half_life" in tests:
        hl = half_life_mean_reversion(close_prices)
        print(f"  Half-Life (MR):        {hl:.1f} days")

    print()


def cmd_store(args: argparse.Namespace) -> None:
    """Inspect stored data."""
    from data.storage.store import DataStore

    store = DataStore()

    if args.list:
        tickers = store.list_tickers()
        if tickers:
            print(f"\nStored tickers ({len(tickers)}):")
            for t in sorted(tickers):
                print(f"  {t}")
        else:
            print("No data stored yet. Run 'fetch' first.")
        return

    if args.info:
        date_range = store.list_date_range(args.info)
        if date_range:
            print(f"\n{args.info}: {date_range[0]} to {date_range[1]}")
        else:
            print(f"No data found for {args.info}")
        return

    if args.stats:
        stats = store.get_stats()
        print(f"\nStorage stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        return


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qr",
        description="Quant Research Platform CLI",
    )
    parser.add_argument(
        "--log-level",
        default=settings.log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # fetch
    fetch = subparsers.add_parser("fetch", help="Fetch data from external sources")
    fetch.add_argument("--source", required=True, help="Data source (yfinance, fred, edgar)")
    fetch.add_argument("--ticker", help="Single ticker symbol")
    fetch.add_argument("--tickers", help="Comma-separated ticker symbols")
    fetch.add_argument("--series", help="FRED series IDs (comma-separated)")
    fetch.add_argument("--start", help="Start date (YYYY-MM-DD)")
    fetch.add_argument("--end", help="End date (YYYY-MM-DD)")
    fetch.add_argument("--interval", default="1d", help="Data interval (1d, 1h, etc.)")
    fetch.add_argument("--filing-type", default="10-K", help="SEC filing type")

    # analyze
    analyze = subparsers.add_parser("analyze", help="Run return/risk analytics")
    analyze.add_argument("--ticker", required=True)
    analyze.add_argument("--metrics", help="Comma-separated metrics")
    analyze.add_argument("--start", help="Start date")
    analyze.add_argument("--end", help="End date")

    # stats
    stats_cmd = subparsers.add_parser("stats", help="Run statistical tests")
    stats_cmd.add_argument("--ticker", required=True)
    stats_cmd.add_argument("--tests", help="Comma-separated tests")
    stats_cmd.add_argument("--start", help="Start date")
    stats_cmd.add_argument("--end", help="End date")

    # store
    store = subparsers.add_parser("store", help="Inspect stored data")
    store.add_argument("--list", action="store_true", help="List stored tickers")
    store.add_argument("--info", help="Show info for a ticker")
    store.add_argument("--stats", action="store_true", help="Show storage stats")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    setup_logging(args.log_level)

    commands = {
        "fetch": cmd_fetch,
        "analyze": cmd_analyze,
        "stats": cmd_stats,
        "store": cmd_store,
    }

    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Command failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
