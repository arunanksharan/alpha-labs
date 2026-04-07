"""FastAPI backend for the Agentic Alpha Lab.

Structured JSON responses for both AI agents and dashboards.
Run with: uvicorn api.server:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic Alpha Lab API",
    description="Agent-native quant research platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ResearchRequest(BaseModel):
    ticker: str
    strategy: str = "mean_reversion"
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 100_000.0


class BacktestRequest(BaseModel):
    signals_csv: str
    prices_csv: str
    initial_capital: float = 100_000.0


class SignalDecayRequest(BaseModel):
    signals_csv: str
    prices_csv: str
    max_horizon: int = 60


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/research")
def run_research(req: ResearchRequest) -> dict:
    """Run full research pipeline. Returns JSON-serialized ResearchResult."""
    from core.orchestrator import ResearchOrchestrator

    orchestrator = ResearchOrchestrator()
    result = orchestrator.run(
        req.ticker, req.strategy, req.start_date, req.end_date, req.initial_capital
    )
    return result.to_json()


@app.post("/api/backtest")
def run_backtest(req: BacktestRequest) -> dict:
    """Quick backtest from CSV data."""
    from core.adapters import csv_to_dataframe
    from core.backtest import BacktestEngineRegistry

    signals = csv_to_dataframe(req.signals_csv)
    prices = csv_to_dataframe(req.prices_csv)
    engine = BacktestEngineRegistry.get("vectorized")
    result = engine.run(signals, prices, req.initial_capital)
    return result.to_json()


@app.post("/api/signal-decay")
def analyze_signal_decay(req: SignalDecayRequest) -> dict:
    """Analyze signal decay (IC curves)."""
    from core.adapters import csv_to_dataframe
    from analytics.signal_decay import SignalDecayAnalyzer

    signals = csv_to_dataframe(req.signals_csv)
    prices = csv_to_dataframe(req.prices_csv)
    analyzer = SignalDecayAnalyzer(max_horizon=req.max_horizon)
    ic_curve = analyzer.compute_ic_curve(signals, prices)
    return {
        "ic_curve": ic_curve.to_dicts(),
        "half_life": analyzer.compute_ic_half_life(ic_curve),
        "summary": analyzer.decay_summary(ic_curve),
    }


@app.get("/api/strategies")
def list_strategies() -> dict:
    """List available strategies."""
    from core.orchestrator import ResearchOrchestrator

    return {"strategies": ResearchOrchestrator().list_strategies()}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "platform": "Agentic Alpha Lab"}
