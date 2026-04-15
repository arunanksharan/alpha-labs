"""FastAPI backend for the Agentic Alpha Lab.

Production-ready with configurable CORS, rate limiting, and WebSocket auth.
Run with: PYTHONPATH=. uvicorn api.server:app --host 0.0.0.0 --port 8100
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import logging
import os
import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic Alpha Lab API",
    description="Agent-native quant research platform",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — configurable via CORS_ORIGINS env var
# ---------------------------------------------------------------------------

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Rate limiting — in-memory, per IP
# ---------------------------------------------------------------------------

_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_GENERAL = int(os.environ.get("RATE_LIMIT_GENERAL", "120"))  # req/min
RATE_LIMIT_AUTH = int(os.environ.get("RATE_LIMIT_AUTH", "10"))  # req/min


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple token-bucket rate limiter per IP."""
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    now = time.time()

    # Determine limit
    limit = RATE_LIMIT_AUTH if path.startswith("/api/auth") else RATE_LIMIT_GENERAL

    # Clean old entries (older than 60s)
    key = f"{client_ip}:{path.split('/')[2] if len(path.split('/')) > 2 else 'general'}"
    _rate_store[key] = [t for t in _rate_store[key] if now - t < 60]

    if len(_rate_store[key]) >= limit:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait before retrying."},
        )

    _rate_store[key].append(now)
    return await call_next(request)


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
    from core.orchestrator import ResearchOrchestrator
    orchestrator = ResearchOrchestrator()
    result = orchestrator.run(req.ticker, req.strategy, req.start_date, req.end_date, req.initial_capital)
    return result.to_json()


@app.post("/api/backtest")
def run_backtest(req: BacktestRequest) -> dict:
    from core.adapters import csv_to_dataframe
    from core.backtest import BacktestEngineRegistry
    signals = csv_to_dataframe(req.signals_csv)
    prices = csv_to_dataframe(req.prices_csv)
    engine = BacktestEngineRegistry.get("vectorized")
    result = engine.run(signals, prices, req.initial_capital)
    return result.to_json()


@app.post("/api/signal-decay")
def analyze_signal_decay(req: SignalDecayRequest) -> dict:
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
    from core.orchestrator import ResearchOrchestrator
    return {"strategies": ResearchOrchestrator().list_strategies()}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "platform": "Agentic Alpha Lab", "version": "1.0.0"}


@app.get("/api/models")
def list_models() -> dict:
    from core.llm import get_available_models, check_api_keys, DEFAULT_MODEL
    return {
        "default_model": DEFAULT_MODEL,
        "api_keys": check_api_keys(),
        "models": get_available_models(),
    }


class LLMTestRequest(BaseModel):
    model: str = "gpt-5-mini"
    prompt: str = "What is the current outlook for equities? Answer in 2 sentences."


@app.post("/api/models/test")
def test_model(req: LLMTestRequest) -> dict:
    from core.llm import llm_call
    response = llm_call(req.prompt, model=req.model)
    return response.to_json()


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from api.auth_routes import router as auth_router  # noqa: E402
from api.agent_routes import router as agent_router  # noqa: E402
from api.chat_routes import router as chat_router  # noqa: E402
from api.cycle_routes import router as cycle_router  # noqa: E402
from api.settings_routes import router as settings_router  # noqa: E402
from api.universe_routes import router as universe_router  # noqa: E402
from api.config_agent_routes import router as config_agent_router  # noqa: E402
from api.job_routes import router as job_router  # noqa: E402
from api.cron_routes import router as cron_router  # noqa: E402
from api.voice_routes import router as voice_router  # noqa: E402
from api.skill_routes import router as skill_router  # noqa: E402
from api.events import event_manager  # noqa: E402

app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(chat_router)
app.include_router(cycle_router)
app.include_router(settings_router)
app.include_router(universe_router)
app.include_router(config_agent_router)
app.include_router(job_router)
app.include_router(cron_router)
app.include_router(voice_router)
app.include_router(skill_router)


# ---------------------------------------------------------------------------
# WebSocket — with optional token auth
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket for real-time event streaming. Validates token if auth is available."""
    token = websocket.query_params.get("token")

    if token:
        try:
            from auth.service import decode_token
            payload = decode_token(token)
            if not payload or payload.get("type") != "access":
                await websocket.close(code=4001, reason="Invalid token")
                return
        except Exception:
            pass

    await event_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        event_manager.disconnect(websocket)


@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket) -> None:
    """Voice research pipeline — Deepgram STT → LLM with tools → text response.

    Protocol:
        Client sends: binary audio chunks (WebM/Opus from MediaRecorder)
                      or JSON {"type": "stop"} to end utterance
        Server sends: JSON messages:
            {"type": "ready"}
            {"type": "transcript", "text": "...", "is_final": bool}
            {"type": "processing", "message": "..."}
            {"type": "tool_call", "tool": "...", "args": {...}}
            {"type": "tool_result", "tool": "...", "result": {...}}
            {"type": "response_chunk", "text": "..."}
            {"type": "response_complete", "text": "..."}
            {"type": "error", "message": "..."}
    """
    await websocket.accept()

    import json as json_mod
    from voice.pipeline import handle_voice_session

    async def send_json(data: dict) -> None:
        try:
            await websocket.send_text(json_mod.dumps(data))
        except Exception:
            pass

    try:
        await handle_voice_session(websocket, send_json)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("Voice WebSocket error: %s", e)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
