"""Agent API routes — live end-to-end pipeline with WebSocket streaming.

Fixes applied:
1. AgentRunner.run() is synchronous → wrapped in asyncio.to_thread()
2. Events broadcast to WebSocket after each agent step
3. ResearchState persisted across run → approve API calls
4. Approval gate pauses pipeline, resumes on human decision
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from api.events import event_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    ticker: str
    strategy: str = "mean_reversion"
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 100_000.0


class ApprovalRequest(BaseModel):
    run_id: str = ""
    approved: bool = True


# Persistent state across API calls
_runs: dict[str, dict[str, Any]] = {}
_states: dict[str, Any] = {}  # run_id → ResearchState (for approval resume)
_approval_events: dict[str, asyncio.Event] = {}
_approval_decisions: dict[str, bool] = {}


def _broadcast_state_events(run_id: str, state: Any) -> None:
    """Broadcast all new events from ResearchState to WebSocket."""
    for evt in state.events:
        if isinstance(evt, dict):
            event_manager.emit_sync({"type": "agent_event", "run_id": run_id, **evt})


def _run_agents_sync(
    run_id: str,
    ticker: str,
    strategy: str,
    start_date: str,
    end_date: str,
    initial_capital: float,
) -> dict:
    """Run agent pipeline synchronously (called from thread pool)."""
    from agents.graph import AgentRunner
    from agents.state import AgentStatus

    runner = AgentRunner()
    state = runner.run(
        ticker=ticker,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
    )

    # Check if approval is needed
    if state.human_approval_required and state.human_approved is None:
        _states[run_id] = (runner, state)
        return {
            "status": "awaiting_approval",
            "events": state.events,
            "signals_count": len(state.signals),
            "risk_assessment": state.risk_assessment,
        }

    return {
        "status": "completed",
        "events": state.events,
        "backtest_result": state.backtest_result,
        "validation_result": state.validation_result,
        "signal_decay": state.signal_decay,
        "signals": state.signals,
    }


def _resume_agents_sync(run_id: str, approved: bool) -> dict:
    """Resume pipeline after human approval (called from thread pool)."""
    if run_id not in _states:
        return {"status": "error", "error": "No pending state for this run"}

    runner, state = _states.pop(run_id)

    if approved:
        state = runner.approve(state)
    else:
        state = runner.reject(state)

    return {
        "status": "completed",
        "events": state.events,
        "backtest_result": state.backtest_result,
        "validation_result": state.validation_result,
        "signal_decay": state.signal_decay,
        "signals": state.signals,
    }


async def _run_pipeline(run_id: str, req: AgentRunRequest) -> None:
    """Execute pipeline in background thread, broadcast events."""
    _runs[run_id]["status"] = "running"
    await event_manager.broadcast(
        {"type": "run_started", "run_id": run_id, "ticker": req.ticker}
    )

    try:
        # FIX 1: run sync code in thread pool (no await on sync function)
        result = await asyncio.to_thread(
            _run_agents_sync,
            run_id,
            req.ticker,
            req.strategy,
            req.start_date,
            req.end_date,
            req.initial_capital,
        )

        _runs[run_id]["status"] = result["status"]
        _runs[run_id]["result"] = result

        # Broadcast all agent events
        for evt in result.get("events", []):
            if isinstance(evt, dict):
                await event_manager.broadcast(
                    {"type": "agent_event", "run_id": run_id, **evt}
                )

        if result["status"] == "awaiting_approval":
            _approval_events[run_id] = asyncio.Event()
            await event_manager.broadcast({
                "type": "awaiting_approval",
                "run_id": run_id,
                "signals_count": result.get("signals_count", 0),
            })

            # Wait for human decision (with timeout)
            try:
                await asyncio.wait_for(_approval_events[run_id].wait(), timeout=300)
            except asyncio.TimeoutError:
                _runs[run_id]["status"] = "timeout"
                await event_manager.broadcast(
                    {"type": "approval_timeout", "run_id": run_id}
                )
                return

            approved = _approval_decisions.pop(run_id, False)
            _approval_events.pop(run_id, None)

            # Resume in thread pool
            resume_result = await asyncio.to_thread(
                _resume_agents_sync, run_id, approved
            )
            _runs[run_id]["status"] = resume_result["status"]
            _runs[run_id]["result"] = resume_result

            for evt in resume_result.get("events", []):
                if isinstance(evt, dict):
                    await event_manager.broadcast(
                        {"type": "agent_event", "run_id": run_id, **evt}
                    )

        await event_manager.broadcast(
            {"type": "run_completed", "run_id": run_id, "result": _runs[run_id].get("result")}
        )

    except Exception as exc:
        logger.exception("Pipeline run %s failed", run_id)
        _runs[run_id]["status"] = "failed"
        _runs[run_id]["error"] = str(exc)
        await event_manager.broadcast(
            {"type": "run_failed", "run_id": run_id, "error": str(exc)}
        )


@router.post("/run")
async def start_run(req: AgentRunRequest) -> dict:
    """Start the multi-agent pipeline. Returns immediately with run_id."""
    run_id = uuid.uuid4().hex[:12]
    _runs[run_id] = {
        "run_id": run_id,
        "status": "pending",
        "request": req.model_dump(),
        "result": None,
        "error": None,
    }
    asyncio.create_task(_run_pipeline(run_id, req))
    return {"run_id": run_id, "status": "pending"}


@router.get("/status")
async def get_status() -> dict:
    """Return agent system status — all runs and pending approvals."""
    return {
        "runs": _runs,
        "pending_approvals": list(_approval_events.keys()),
        "latest_events": event_manager.get_history()[-20:],
    }


@router.post("/approve")
async def approve_signals(req: ApprovalRequest) -> dict:
    """Approve or reject pending signals. Unblocks the paused pipeline."""
    # Find the right run_id
    run_id = req.run_id
    if not run_id and _approval_events:
        run_id = next(iter(_approval_events))

    if run_id not in _approval_events:
        raise HTTPException(status_code=404, detail="No pending approval for this run")

    _approval_decisions[run_id] = req.approved
    _approval_events[run_id].set()

    action = "approved" if req.approved else "rejected"
    await event_manager.broadcast(
        {"type": "approval_decision", "run_id": run_id, "decision": action}
    )
    return {"run_id": run_id, "decision": action}


@router.get("/events")
async def get_events() -> dict:
    """Return full event history."""
    return {"events": event_manager.get_history()}


@router.websocket("/ws")
async def agent_websocket(websocket: WebSocket) -> None:
    """Real-time event stream for dashboard."""
    await event_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        event_manager.disconnect(websocket)
