"""Universe management + pre-computed research results API.

Serves cached research results so the dashboard loads instantly.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/universe", tags=["universe"])

UNIVERSE_FILE = Path("data/universe.json")
CACHE_DIR = Path("data/cache/research")

DEFAULT_UNIVERSE = {
    "tickers": [
        "D05.SI", "O39.SI", "U11.SI", "C6L.SI",
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
        "AAPL", "NVDA",
    ],
    "start_date": "2022-01-01",
    "strategies": ["mean_reversion", "momentum"],
}


def _load_universe() -> dict:
    if UNIVERSE_FILE.exists():
        return json.loads(UNIVERSE_FILE.read_text())
    return DEFAULT_UNIVERSE


def _save_universe(universe: dict) -> None:
    UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    UNIVERSE_FILE.write_text(json.dumps(universe, indent=2))


# ---------------------------------------------------------------------------
# Universe CRUD
# ---------------------------------------------------------------------------


@router.get("")
def get_universe() -> dict:
    """Return the current research universe."""
    universe = _load_universe()

    # Enrich with cached result status
    tickers_status = []
    for ticker in universe["tickers"]:
        cached_strategies = []
        for strategy in universe.get("strategies", []):
            cache_file = CACHE_DIR / f"{ticker}__{strategy}.json"
            if cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text())
                    bt = data.get("backtest", {})
                    cached_strategies.append({
                        "strategy": strategy,
                        "signals": data.get("signals_count", 0),
                        "sharpe": bt.get("sharpe_ratio", 0),
                        "total_return": bt.get("total_return", 0),
                        "cached": True,
                    })
                except Exception:
                    cached_strategies.append({"strategy": strategy, "cached": False})
            else:
                cached_strategies.append({"strategy": strategy, "cached": False})

        tickers_status.append({
            "ticker": ticker,
            "strategies": cached_strategies,
            "has_data": any(s.get("cached") for s in cached_strategies),
        })

    return {
        "tickers": universe["tickers"],
        "start_date": universe.get("start_date", "2022-01-01"),
        "strategies": universe.get("strategies", ["mean_reversion"]),
        "status": tickers_status,
    }


class AddTickerRequest(BaseModel):
    ticker: str


@router.post("/add")
def add_ticker(req: AddTickerRequest) -> dict:
    """Add a ticker to the research universe."""
    universe = _load_universe()
    ticker = req.ticker.strip().upper()
    if ticker not in universe["tickers"]:
        universe["tickers"].append(ticker)
        _save_universe(universe)
        logger.info("Added %s to universe", ticker)
    return {"tickers": universe["tickers"]}


@router.post("/remove")
def remove_ticker(req: AddTickerRequest) -> dict:
    """Remove a ticker from the research universe."""
    universe = _load_universe()
    ticker = req.ticker.strip().upper()
    universe["tickers"] = [t for t in universe["tickers"] if t != ticker]
    _save_universe(universe)
    return {"tickers": universe["tickers"]}


# ---------------------------------------------------------------------------
# Cached research results
# ---------------------------------------------------------------------------


@router.get("/results/{ticker}")
def get_cached_result(ticker: str, strategy: str = "mean_reversion") -> dict:
    """Return cached research result for a ticker + strategy."""
    cache_file = CACHE_DIR / f"{ticker.upper()}__{strategy}.json"
    if not cache_file.exists():
        return {"cached": False, "ticker": ticker, "strategy": strategy}

    try:
        data = json.loads(cache_file.read_text())
        return {"cached": True, **data}
    except Exception as e:
        return {"cached": False, "error": str(e)}


@router.get("/signals")
def get_all_signals() -> dict:
    """Return the latest signals across all cached tickers."""
    universe = _load_universe()
    all_signals = []

    for ticker in universe["tickers"]:
        for strategy in universe.get("strategies", ["mean_reversion"]):
            cache_file = CACHE_DIR / f"{ticker}__{strategy}.json"
            if cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text())
                    bt = data.get("backtest", {})
                    all_signals.append({
                        "ticker": ticker,
                        "strategy": strategy,
                        "signals_count": data.get("signals_count", 0),
                        "total_return": bt.get("total_return", 0),
                        "sharpe_ratio": bt.get("sharpe_ratio", 0),
                        "max_drawdown": bt.get("max_drawdown", 0),
                        "win_rate": bt.get("win_rate", 0),
                    })
                except Exception:
                    pass

    return {"signals": all_signals, "count": len(all_signals)}


@router.post("/refresh/{ticker}")
def refresh_ticker(ticker: str, strategy: str = "mean_reversion") -> dict:
    """Fetch latest data and re-run research pipeline for a single ticker."""
    from core.orchestrator import ResearchOrchestrator
    from data.fetchers.yfinance_connector import YFinanceConnector
    from data.storage.store import DataStore
    from datetime import date

    universe = _load_universe()
    start_date = universe.get("start_date", "2022-01-01")
    end = date.today().isoformat()

    # Step 1: Fetch fresh data
    try:
        connector = YFinanceConnector()
        store = DataStore()
        data = connector.fetch_ohlcv(ticker, start_date, end)
        store.save_ohlcv(ticker, data, source="yfinance")
    except Exception as e:
        return {"error": f"Data fetch failed: {e}"}

    # Step 2: Run research
    try:
        orchestrator = ResearchOrchestrator()
        result = orchestrator.run(ticker, strategy, start_date, end)
        result_json = result.to_json()

        # Cache
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{ticker.upper()}__{strategy}.json"
        cache_file.write_text(json.dumps(result_json, default=str))

        return {"status": "refreshed", "ticker": ticker, "strategy": strategy, **result_json}
    except Exception as e:
        return {"error": f"Research failed: {e}"}
