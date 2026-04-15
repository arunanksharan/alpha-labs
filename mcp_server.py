"""MCP Server for the Agentic Alpha Lab.

Exposes the quant research platform as Model Context Protocol tools
that any AI agent (Claude, Cursor, Windsurf, etc.) can use.

Two modes:
1. Auto-exposed: All FastAPI endpoints become MCP tools automatically
2. Custom tools: Purpose-built research tools with rich descriptions

Run:
    # Standalone MCP server (stdio transport for Claude Desktop)
    python mcp_server.py

    # Or mount on the existing FastAPI app (SSE transport for Cursor)
    # Already mounted at /mcp when the main server starts
"""

from __future__ import annotations

import json
import logging
import os
import sys

# Ensure project is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastmcp import FastMCP

mcp = FastMCP(
    "Agentic Alpha Lab",
    instructions="""You have access to a quantitative research platform that can:
- Analyze any stock ticker with 6 specialist AI agents (Quant, Technician, Sentiment, Fundamentalist, Macro, Contrarian)
- Run backtests with custom parameters (strategy, commission, slippage, entry threshold, lookback window)
- Fetch real-time market data from YFinance (SGX, NSE, NYSE)
- Check current trading signals for a universe of 17 tracked tickers
- Compute risk metrics (VaR, Sharpe, Sortino, max drawdown)

Supported tickers include:
- Singapore: D05.SI (DBS), O39.SI (OCBC), U11.SI (UOB), C6L.SI (SIA)
- India: RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, SBIN.NS, ITC.NS
- US: AAPL, NVDA, MSFT, GOOG, META, AMZN, TSLA

Best demo parameters: NVDA, mean_reversion, 2023-06-01, threshold=1.5, window=30
""",
)


# ---------------------------------------------------------------------------
# Tool 1: Research a stock ticker (6-agent analysis)
# ---------------------------------------------------------------------------

@mcp.tool
def research_ticker(ticker: str) -> str:
    """Analyze a stock using 6 specialist AI agents.

    Runs quantitative (z-scores, momentum), technical (RSI, MACD, Bollinger),
    sentiment (FinBERT), fundamental (DCF, PE), macro (VIX, yield curve),
    and contrarian (short interest, crowding) analysis.

    Returns consensus signal (bullish/bearish/neutral), confidence,
    and reasoning from each agent.

    Args:
        ticker: Stock ticker (e.g., D05.SI, RELIANCE.NS, AAPL, NVDA)
    """
    from agents.specialists.research_director import ResearchDirector

    director = ResearchDirector()
    result = director.answer_question(f"Analyze {ticker}", context={})

    answer = result.get("answer", "")
    traces = result.get("agent_traces", [])
    citations = result.get("citations", [])

    output = f"## Analysis: {ticker}\n\n{answer}\n\n"
    output += "### Agent Findings\n"
    for t in traces:
        agent = t.get("agent", "?")
        signal = t.get("signal", "neutral")
        conf = t.get("confidence", 0)
        thoughts = t.get("thoughts", [])
        output += f"- **{agent}**: {signal} ({conf:.0%}) — {thoughts[0] if thoughts else 'N/A'}\n"

    output += f"\n### Suggested Actions\n"
    for a in result.get("actions", []):
        output += f"- {a}\n"

    return output


# ---------------------------------------------------------------------------
# Tool 2: Run a backtest
# ---------------------------------------------------------------------------

@mcp.tool
def run_backtest(
    ticker: str,
    strategy: str = "mean_reversion",
    start_date: str = "2023-06-01",
    end_date: str = "2025-12-31",
    commission_bps: float = 5.0,
    slippage_bps: float = 2.0,
    entry_threshold: float = 2.0,
    lookback_window: int = 20,
    initial_capital: float = 100000.0,
) -> str:
    """Run a backtest for a trading strategy on historical data.

    Returns total return, Sharpe ratio, win rate, max drawdown,
    and other performance metrics.

    Best demo params: NVDA, mean_reversion, 2023-06-01, threshold=1.5, window=30

    Args:
        ticker: Stock ticker (e.g., NVDA, D05.SI, RELIANCE.NS)
        strategy: Strategy name (mean_reversion or momentum)
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        commission_bps: Commission in basis points (default 5)
        slippage_bps: Slippage in basis points (default 2)
        entry_threshold: Z-score entry threshold for mean reversion (default 2.0)
        lookback_window: Lookback window in days (default 20)
        initial_capital: Starting capital (default 100000)
    """
    from jobs.wrapper import run_research_job
    from jobs.models import BacktestConfig

    result = run_research_job(
        ticker=ticker,
        strategy_name=strategy,
        start_date=start_date,
        end_date=end_date,
        config=BacktestConfig(
            initial_capital=initial_capital,
            commission=commission_bps / 10000,
            slippage=slippage_bps / 10000,
            strategy_params={
                "entry_threshold": entry_threshold,
                "window": lookback_window,
            },
        ),
    )

    bt = result.get("backtest", {})
    signals = result.get("signals_count", 0)

    output = f"## Backtest: {ticker} ({strategy})\n"
    output += f"**Period**: {start_date} → {end_date}\n"
    output += f"**Config**: capital=${initial_capital:,.0f}, commission={commission_bps}bps, slippage={slippage_bps}bps\n"
    output += f"**Strategy params**: threshold={entry_threshold}σ, window={lookback_window}d\n\n"

    output += "### Results\n"
    output += f"| Metric | Value |\n|--------|-------|\n"
    output += f"| Total Return | {bt.get('total_return', 0) * 100:.1f}% |\n"
    output += f"| Sharpe Ratio | {bt.get('sharpe_ratio', 0):.2f} |\n"
    output += f"| Sortino Ratio | {bt.get('sortino_ratio', 0):.2f} |\n"
    output += f"| Max Drawdown | {bt.get('max_drawdown', 0) * 100:.1f}% |\n"
    output += f"| Win Rate | {bt.get('win_rate', 0) * 100:.0f}% |\n"
    output += f"| Signals Generated | {signals} |\n"
    output += f"| Equity Curve Points | {len(bt.get('equity_curve', []))} |\n"
    output += f"| Trades | {len(bt.get('trades', []))} |\n"

    var = bt.get("var_95")
    if var is not None:
        output += f"| VaR 95% | {var * 100:.2f}% |\n"

    return output


# ---------------------------------------------------------------------------
# Tool 3: Get current signals
# ---------------------------------------------------------------------------

@mcp.tool
def get_signals() -> str:
    """Get current trading signals for all tickers in the research universe.

    Shows which stocks are signaling long, short, or neutral based on
    the most recent cached analysis.
    """
    from pathlib import Path

    cache_dir = Path("data/cache/research")
    signals = []

    if cache_dir.exists():
        for f in cache_dir.glob("*__mean_reversion.json"):
            try:
                data = json.loads(f.read_text())
                bt = data.get("backtest", {})
                ticker = data.get("ticker", f.stem.split("__")[0])
                ret = bt.get("total_return", 0)
                sharpe = bt.get("sharpe_ratio", 0)
                wr = bt.get("win_rate", 0)
                direction = "LONG" if ret > 0.01 else "SHORT" if ret < -0.01 else "NEUTRAL"
                signals.append((ticker, direction, ret, sharpe, wr))
            except Exception:
                pass

    signals.sort(key=lambda s: abs(s[2]), reverse=True)

    output = "## Current Signals\n\n"
    output += "| Ticker | Direction | Return | Sharpe | Win Rate |\n"
    output += "|--------|-----------|--------|--------|----------|\n"
    for ticker, direction, ret, sharpe, wr in signals:
        output += f"| {ticker} | {direction} | {ret * 100:+.1f}% | {sharpe:.2f} | {wr * 100:.0f}% |\n"

    output += f"\n*{len(signals)} signals from cached universe analysis*"
    return output


# ---------------------------------------------------------------------------
# Tool 4: Fetch market data
# ---------------------------------------------------------------------------

@mcp.tool
def fetch_market_data(ticker: str, period: str = "1mo") -> str:
    """Fetch recent OHLCV market data for a ticker from YFinance.

    Args:
        ticker: Stock ticker (e.g., D05.SI, AAPL, NVDA)
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y)
    """
    import yfinance as yf

    data = yf.download(ticker, period=period, progress=False)
    if data.empty:
        return f"No data found for {ticker}"

    output = f"## Market Data: {ticker} ({period})\n\n"
    output += f"**Latest Close**: ${float(data['Close'].iloc[-1].iloc[0]):.2f}\n"
    output += f"**Period High**: ${float(data['High'].max().iloc[0]):.2f}\n"
    output += f"**Period Low**: ${float(data['Low'].min().iloc[0]):.2f}\n"
    output += f"**Data Points**: {len(data)}\n\n"

    output += "### Recent Prices\n"
    output += "| Date | Close | Volume |\n|------|-------|--------|\n"
    for idx in data.tail(5).index:
        row = data.loc[idx]
        date_str = str(idx.date()) if hasattr(idx, 'date') else str(idx)[:10]
        close = float(row['Close'].iloc[0])
        vol = int(row['Volume'].iloc[0])
        output += f"| {date_str} | ${close:.2f} | {vol:,} |\n"

    return output


# ---------------------------------------------------------------------------
# Tool 5: Get platform status
# ---------------------------------------------------------------------------

@mcp.tool
def get_platform_status() -> str:
    """Get the current status of the Agentic Alpha Lab platform.

    Shows available tickers, cached data, configured API keys,
    and system health.
    """
    from pathlib import Path

    output = "## Platform Status\n\n"

    # Universe
    universe_file = Path("data/universe.json")
    if universe_file.exists():
        universe = json.loads(universe_file.read_text())
        tickers = universe.get("tickers", [])
        output += f"**Universe**: {len(tickers)} tickers\n"
        output += f"  {', '.join(tickers)}\n\n"

    # Cached data
    cache_dir = Path("data/cache/research")
    cached = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    output += f"**Cached Research**: {len(cached)} results\n"

    # Parquet store
    store_dir = Path("data/store/ohlcv")
    if store_dir.exists():
        parquet_tickers = [d.name for d in store_dir.iterdir() if d.is_dir()]
        output += f"**OHLCV Data**: {len(parquet_tickers)} tickers in Parquet store\n"

    # API keys
    from core.llm import check_api_keys
    keys = check_api_keys()
    configured = [k for k, v in keys.items() if v]
    output += f"**LLM Providers**: {', '.join(configured) if configured else 'none'}\n"

    # Default model
    from core.llm import DEFAULT_MODEL
    output += f"**Default Model**: {DEFAULT_MODEL}\n"

    return output


# ---------------------------------------------------------------------------
# Main — run as standalone MCP server (stdio transport)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
